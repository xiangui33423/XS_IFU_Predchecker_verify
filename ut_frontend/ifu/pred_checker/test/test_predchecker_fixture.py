import toffee_test
from comm import get_version_checker

from dut.PredChecker import DUTPredChecker
from comm.functions import UT_FCOV, module_name_with
import toffee.funcov as fc
from toffee import *

version_check = get_version_checker("openxiangshan-kmh-*")

gr = fc.CovGroup(UT_FCOV("../../../TOFFEE"))
# gr = fc.CovGroup("114514")

from ..env import PredCheckerEnv

@toffee_test.fixture
async def pred_checker(toffee_request: toffee_test.ToffeeRequest):
    import asyncio
    version_check()
    dut = toffee_request.create_dut(DUTPredChecker)
    start_clock(dut)

    checker = PredCheckerEnv(dut)
    yield checker

    cur_loop = asyncio.get_event_loop()
    for task in asyncio.all_tasks(cur_loop):
        if task.get_name() == "__clock_loop":
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                break