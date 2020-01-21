#!/usr/bin/env python3

# Copyright (c) 2015-2019 Clearmatics Technologies Ltd
#
# SPDX-License-Identifier: LGPL-3.0+

# Parse the arguments given to the script

from __future__ import annotations
from . import constants
from . import errors

import argparse
import sys
import os
from os.path import join, dirname, normpath
# Import Pynacl required modules
import eth_abi
import nacl.utils  # type: ignore
from nacl.public import PrivateKey, PublicKey, Box  # type: ignore
from web3 import Web3, HTTPProvider  # type: ignore
from py_ecc import bn128 as ec
from typing import List, Tuple, Union, Any, cast


def open_web3(url: str) -> Any:
    """
    Create a Web3 context from an http URL.
    """
    return Web3(HTTPProvider(url))


FQ = ec.FQ
G1 = Tuple[ec.FQ, ec.FQ]


class EtherValue:
    """
    Representation of some amount of Ether (or any token) in terms of Wei.
    Disambiguates Ether values from other units such as zeth_units.
    """
    def __init__(self, val: Union[str, int, float], units: str = 'ether'):
        self.wei = Web3.toWei(val, units)

    def __str__(self) -> str:
        return str(self.wei)

    def __add__(self, other: EtherValue) -> EtherValue:
        return EtherValue(self.wei + other.wei, 'wei')

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, EtherValue):
            return False
        return self.wei == other.wei

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def ether(self) -> str:
        return str(Web3.fromWei(self.wei, 'ether'))


def encode_single(type_name: str, data: bytes) -> bytes:
    """
    Typed wrapper around eth_abi.encode_single
    """
    return eth_abi.encode_single(type_name, data)  # type: ignore


def encode_abi(type_names: List[str], data: List[bytes]) -> bytes:
    """
    Typed wrapper around eth_abi.encode_abi
    """
    return eth_abi.encode_abi(type_names, data)  # type: ignore


def encode_g1_to_bytes(group_el: G1) -> bytes:
    """
    Encode a group element into a byte string
    We assume here the group prime $p$ is written in less than 256 bits
    to conform with Ethereum bytes32 type.
    """
    return \
        int(group_el[0]).to_bytes(32, byteorder='big') + \
        int(group_el[1]).to_bytes(32, byteorder='big')


def int64_to_hex(number: int) -> str:
    return '{:016x}'.format(number)


def hex_digest_to_binary_string(digest: str) -> str:
    if len(digest) % 2 == 1:
        digest = "0" + digest
    return "".join(["{0:04b}".format(int(c, 16)) for c in digest])


def digest_to_binary_string(digest: bytes) -> str:
    return "".join(["{0:08b}".format(b) for b in digest])


def hex_to_int(elements: List[str]) -> List[int]:
    """
    Given an array of hex strings, return an array of int values
    """
    return [int(x, 16) for x in elements]


def hex_extend_32bytes(element: str) -> str:
    """
    Extend a hex string to represent 32 bytes
    """
    res = str(element)
    if len(res) % 2 != 0:
        res = "0" + res
    res = "00"*int((64-len(res))/2) + res
    return res


def get_private_key_from_bytes(sk_bytes: bytes) -> PrivateKey:
    """
    Gets PrivateKey object from raw representation
    (see: https://pynacl.readthedocs.io/en/stable/public/#nacl.public.PrivateKey)
    """
    return PrivateKey(sk_bytes, encoder=nacl.encoding.RawEncoder)


def get_public_key_from_bytes(pk_bytes: bytes) -> PublicKey:
    """
    Gets PublicKey object from raw representation
    (see: https://pynacl.readthedocs.io/en/stable/public/#nacl.public.PublicKey)
    """
    return PublicKey(pk_bytes, encoder=nacl.encoding.RawEncoder)


def encrypt(message: str, pk_receiver: PublicKey, sk_sender: PrivateKey) -> bytes:
    """
    Encrypts a string message by using valid ec25519 public key and
    private key objects. See: https://pynacl.readthedocs.io/en/stable/public/
    """
    # Init encryption box instance
    encryption_box = Box(sk_sender, pk_receiver)

    # Encode str message to bytes
    message_bytes = message.encode('utf-8')

    # Encrypt the message. The nonce is chosen randomly.
    encrypted = encryption_box.encrypt(
        message_bytes,
        encoder=nacl.encoding.RawEncoder)

    # Need to cast to the parent class Bytes of nacl.utils.EncryptedMessage
    # to make it accepted from `Mix` Solidity function
    return bytes(encrypted)


def decrypt(
        encrypted_message: bytes,
        pk_sender: PublicKey,
        sk_receiver: PrivateKey) -> str:
    """
    Decrypts a string message by using valid ec25519 public key and private key
    objects.  See: https://pynacl.readthedocs.io/en/stable/public/
    """
    assert(isinstance(pk_sender, PublicKey)), \
        f"PublicKey: {pk_sender} ({type(pk_sender)})"
    assert(isinstance(sk_receiver, PrivateKey)), \
        f"PrivateKey: {sk_receiver} ({type(sk_receiver)})"

    # Init encryption box instance
    decryption_box = Box(sk_receiver, pk_sender)

    # Check integrity of the ciphertext and decrypt it
    message = decryption_box.decrypt(encrypted_message)
    return str(message, encoding='utf-8')


def convert_leaf_address_to_node_address(
        address_leaf: int, tree_depth: int) -> int:
    """
    Converts the relative address of a leaf to an absolute address in the tree
    Important note: The merkle root index is 0 (not 1!)
    """
    address = address_leaf + (2 ** tree_depth - 1)
    if address > (2 ** (tree_depth + 1) - 1):
        return -1
    return address


def compute_merkle_path(
        address_commitment: int,
        tree_depth: int,
        byte_tree: List[bytes]) -> List[str]:
    merkle_path: List[str] = []
    address_bits = []
    address = convert_leaf_address_to_node_address(address_commitment, tree_depth)
    if address == -1:
        return merkle_path  # return empty merkle_path
    for _ in range(0, tree_depth):
        address_bits.append(address % 2)
        if (address % 2) == 0:
            # [2:] to strip the 0x prefix
            merkle_path.append(Web3.toHex(byte_tree[address - 1])[2:])
            # -1 because we decided to start counting from 0 (which is the
            # index of the root node)
            address = int(address/2) - 1
        else:
            merkle_path.append(Web3.toHex(byte_tree[address + 1])[2:])
            address = int(address/2)
    return merkle_path


def parse_zksnark_arg() -> str:
    """
    Parse the zksnark argument and return its value
    """
    parser = argparse.ArgumentParser(
        description="Testing Zeth transactions using the specified zkSNARK " +
        "('GROTH16' or 'PGHR13').\nNote that the zkSNARK must match the one " +
        "used on the prover server.")
    parser.add_argument("zksnark", help="Set the zkSNARK to use")
    args = parser.parse_args()
    if args.zksnark not in constants.VALID_ZKSNARKS:
        return sys.exit(errors.SNARK_NOT_SUPPORTED)
    return args.zksnark


def get_zeth_dir() -> str:
    return os.environ.get(
        'ZETH',
        normpath(join(dirname(__file__), "..", "..")))


def get_trusted_setup_dir() -> str:
    return os.environ.get(
        'ZETH_TRUSTED_SETUP_DIR',
        join(get_zeth_dir(), "trusted_setup"))


def get_contracts_dir() -> str:
    return os.environ.get(
        'ZETH_CONTRACTS_DIR',
        join(get_zeth_dir(), "zeth-contracts", "contracts"))


def string_list_flatten(
        strs_list: Union[List[str], List[Union[str, List[str]]]]) -> List[str]:
    """
    Flatten a list containing strings or lists of strings.
    """
    if any(isinstance(el, (list, tuple)) for el in strs_list):
        strs: List[str] = []
        for el in strs_list:
            if isinstance(el, (list, tuple)):
                strs.extend(el)
            else:
                strs.append(cast(str, el))
        return strs

    return cast(List[str], strs_list)


def encode_message_to_bytes(message_list: Any) -> bytes:
    # message_list: Union[List[str], List[Union[int, str, List[str]]]]) -> bytes:
    """
    Encode a list of variables, or list of lists of variables into a byte
    vector
    """

    messages = string_list_flatten(message_list)

    data_bytes = bytearray()
    for m in messages:
        # For each element
        m_hex = m

        # Convert it into a hex
        if isinstance(m, int):
            m_hex = "{0:0>4X}".format(m)
        elif isinstance(m, str) and (m[1] == "x"):
            m_hex = m[2:]

        # [SANITY CHECK] Make sure the hex is 32 byte long
        m_hex = hex_extend_32bytes(m_hex)

        # Encode the hex into a byte array and append it to result
        data_bytes += encode_single("bytes32", bytes.fromhex(m_hex))

    return data_bytes


def field_elements_to_hex(longfield: str, shortfield: str) -> str:
    """
    Encode a 256 bit array written over two field elements into a single 32
    byte long hex

    if A= x0 ... x255 and B = y0 ... y7, returns R = hex(x255 ... x3 || y7 y6 y5)
    """
    # Convert longfield into a 253 bit long array
    long_bit = "{0:b}".format(int(longfield, 16))
    if len(long_bit) > 253:
        long_bit = long_bit[:253]
    long_bit = "0"*(253-len(long_bit)) + long_bit

    # Convert shortfield into a 3 bit long array
    short_bit = "{0:b}".format(int(shortfield, 16))
    if len(short_bit) < 3:
        short_bit = "0"*(3-len(short_bit)) + short_bit

    # Reverse the bit arrays
    reversed_long = long_bit[::-1]
    reversed_short = short_bit[::-1]

    # Fill the result 256 bit long array
    res = reversed_long[:253]
    res += reversed_short[:3]
    res = hex_extend_32bytes("{0:0>4X}".format(int(res, 2)))

    return res


def short_commitment(cm: bytes) -> str:
    """
    Summary of the commitment value, in some standard format.
    """
    return cm[0:4].hex()
