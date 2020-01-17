# Copyright (c) 2015-2019 Clearmatics Technologies Ltd
#
# SPDX-License-Identifier: LGPL-3.0+

from commands.utils import open_web3_from_ctx, load_zeth_address_secret, \
    open_wallet, load_mixer_description_from_ctx
from zeth.utils import EtherValue
from click import command, option, pass_context
from typing import Any


@command()
@option("--balance", is_flag=True, help="Show total balance")
@option("--spent", is_flag=True, help="Show spent notes")
@pass_context
def ls_notes(ctx: Any, balance: bool, spent: bool) -> None:
    """
    List the set of notes owned by this wallet
    """
    web3 = open_web3_from_ctx(ctx)
    mixer_desc = load_mixer_description_from_ctx(ctx)
    mixer_instance = mixer_desc.mixer.instantiate(web3)
    js_secret = load_zeth_address_secret(ctx)
    wallet = open_wallet(mixer_instance, js_secret, ctx)

    total = EtherValue(0)
    for addr, short_commit, value in wallet.note_summaries():
        print(f"{short_commit}: value={value.ether()}, addr={addr}")
        total = total + value

    if balance:
        print(f"TOTAL BALANCE: {total.ether()}")

    if not spent:
        return

    print("SPENT NOTES:")
    for addr, short_commit, value in wallet.spent_note_summaries():
        print(f"{short_commit}: value={value.ether()}, addr={addr}")
