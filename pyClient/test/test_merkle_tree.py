# Copyright (c) 2015-2019 Clearmatics Technologies Ltd
#
# SPDX-License-Identifier: LGPL-3.0+


from zeth.merkle_tree import MerkleTree, PersistentMerkleTree, ZERO_ENTRY
from os.path import exists, join
from os import makedirs
from shutil import rmtree
from unittest import TestCase

MERKLE_TREE_TEST_DIR = "_merkle_tests"
MERKLE_TREE_TEST_SIZE = 16


class TestMerkleTree(TestCase):

    @staticmethod
    def setUpClass() -> None:
        TestMerkleTree.tearDownClass()
        makedirs(MERKLE_TREE_TEST_DIR)

    @staticmethod
    def tearDownClass() -> None:
        if exists(MERKLE_TREE_TEST_DIR):
            print(f"Removing test dir: {MERKLE_TREE_TEST_DIR}")
            rmtree(MERKLE_TREE_TEST_DIR)

    @staticmethod
    def _test_vector_to_bytes32(value: int) -> bytes:
        return value.to_bytes(32, byteorder='big')

    def _expected_empty(self) -> bytes:
        self.assertEqual(16, MERKLE_TREE_TEST_SIZE)
        # Test vector generated by test_mimc.py
        return self._test_vector_to_bytes32(
            1792447880902456454889084480864374954299744757125100424674028184042059183092)  # noqa

    def test_combine(self) -> None:
        # Use test vectors used to test the MiMC contract (generated in
        # test_mimc.py)

        left = self._test_vector_to_bytes32(
            3703141493535563179657531719960160174296085208671919316200479060314459804651)  # noqa
        right = self._test_vector_to_bytes32(
            15683951496311901749339509118960676303290224812129752890706581988986633412003)  # noqa
        expect = self._test_vector_to_bytes32(
            16797922449555994684063104214233396200599693715764605878168345782964540311877)  # noqa

        result = MerkleTree.combine(left, right)
        self.assertEqual(expect, result)

    def test_empty(self) -> None:
        mktree = MerkleTree.empty_with_size(MERKLE_TREE_TEST_SIZE)
        root = mktree.compute_root()
        num_entries = mktree.get_num_entries()

        self.assertEqual(0, num_entries)
        self.assertEqual(self._expected_empty(), root)

    def test_empty_save_load(self) -> None:
        mktree_file = join(MERKLE_TREE_TEST_DIR, "empty_save_load")
        mktree = PersistentMerkleTree.open(mktree_file, MERKLE_TREE_TEST_SIZE)
        mktree.save()

        mktree = PersistentMerkleTree.open(mktree_file, MERKLE_TREE_TEST_SIZE)
        root = mktree.compute_root()
        mktree.save()

        self.assertEqual(self._expected_empty(), root)

    def test_single_entry(self) -> None:
        mktree_file = join(MERKLE_TREE_TEST_DIR, "single")
        data = bytes.fromhex("aabbccdd")

        mktree = PersistentMerkleTree.open(mktree_file, MERKLE_TREE_TEST_SIZE)
        mktree.set_entry(0, data)
        self.assertEqual(1, mktree.get_num_entries())
        self.assertEqual(data, mktree.get_entry(0))
        self.assertEqual(ZERO_ENTRY, mktree.get_entry(1))
        root_1 = mktree.compute_root()
        self.assertNotEqual(self._expected_empty(), root_1)
        mktree.save()

        mktree = PersistentMerkleTree.open(mktree_file, MERKLE_TREE_TEST_SIZE)
        self.assertEqual(1, mktree.get_num_entries())
        self.assertEqual(data, mktree.get_entry(0))
        self.assertEqual(ZERO_ENTRY, mktree.get_entry(1))
        root_2 = mktree.compute_root()
        self.assertEqual(root_1, root_2)
