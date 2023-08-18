import ape
import pytest

from curve_dao import CURVE_DAO_OWNERSHIP, CURVE_DAO_PARAM
from curve_dao.modules.smartwallet_checker import (SMARTWALLET_CHECKER,
                                                   whitelist_vecrv_lock)
from curve_dao.simulate import simulate
from curve_dao.vote_utils import make_vote


@pytest.fixture(scope="module")
def tricrypto_pool():
    # TriCryptoINV
    yield ape.Contract("0x5426178799ee0a0181a89b4f57efddfab49941ec")
    # TriCRV
    # yield ape.Contract("0x4ebdf703948ddcea3b11f675b4d1fba9d2414a14")


def test_ramp_parameters(vote_deployer, tricrypto_pool):
    week_seconds = 7 * 86400
    block = ape.chain.blocks[-1]
    last_timestamp = block.timestamp

    future_A = 1707650
    future_gamma = 11809167829000
    future_time = last_timestamp + 2 * week_seconds

    parameter_action = (
        tricrypto_pool.address,
        "ramp_A_gamma",
        future_A,
        future_gamma,
        future_time,
    )

    assert tricrypto_pool.A() != future_A
    assert tricrypto_pool.gamma() != future_gamma

    tx = make_vote(
        target=CURVE_DAO_OWNERSHIP,  # tricrypto-ng factory admin is OWNERSHIP agent
        actions=[parameter_action],
        description="test",
        vote_creator=vote_deployer,
    )

    for log in tx.decode_logs():
        vote_id = log.event_arguments["voteId"]
        break

    # this advances the chain one week from vote creation
    simulate(
        vote_id=vote_id,
        voting_contract=CURVE_DAO_OWNERSHIP["voting"],
    )

    # need to advance another week to finish the ramp
    ape.chain.mine(deltatime=week_seconds)

    assert tricrypto_pool.A() == future_A
    assert tricrypto_pool.gamma() == future_gamma


def test_commit_parameters(vote_deployer, tricrypto_pool):
    """
    TriCryptoINV
    A: 1707629
    gamma: 11809167828997
    mid_fee: 3000000
    out_fee: 30000000
    fee_gamma: 500000000000000
    new_allowed_extra_profit: 2000000000000
    new_adjustment_step: 490000000000000
    new_ma_time: 1801

    TriCRV
    A: 2700000
    gamma: 1300000000000
    mid_fee: 2999999
    out_fee: 80000000
    fee_gamma: 350000000000000
    new_allowed_extra_profit: 100000000000
    new_adjustment_step: 100000000000
    new_ma_time: 600
    """
    # new
    new_mid_fee = 2000000
    new_out_fee = 4500000
    # same as TriCRV
    new_fee_gamma = 350000000000000
    new_allowed_extra_profit = 100000000000
    new_adjustment_step = 100000000000
    new_ma_time = 600

    parameter_action = (
        tricrypto_pool.address,
        "commit_new_parameters",
        new_mid_fee,
        new_out_fee,
        new_fee_gamma,
        new_allowed_extra_profit,
        new_adjustment_step,
        new_ma_time,
    )

    assert tricrypto_pool.mid_fee() != new_mid_fee
    assert tricrypto_pool.out_fee() != new_out_fee

    tx = make_vote(
        target=CURVE_DAO_OWNERSHIP,  # tricrypto-ng factory admin is OWNERSHIP agent
        actions=[parameter_action],
        description="test",
        vote_creator=vote_deployer,
    )

    for log in tx.decode_logs():
        vote_id = log.event_arguments["voteId"]
        break

    # this advances the chain one week from vote creation
    simulate(
        vote_id=vote_id,
        voting_contract=CURVE_DAO_OWNERSHIP["voting"],
    )

    # admin actions delay is 3 days
    ape.chain.mine(deltatime=3 * 86400)
    tricrypto_pool.apply_new_parameters(sender=vote_deployer)

    assert tricrypto_pool.mid_fee() == new_mid_fee
    assert tricrypto_pool.out_fee() == new_out_fee
