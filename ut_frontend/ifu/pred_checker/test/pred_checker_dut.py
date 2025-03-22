import toffee_test
import toffee
from ..env import PredCheckerEnv
from dut.PredChecker import DUTPredChecker
from comm.functions import UT_FCOV, module_name_with
import toffee.funcov as fc
from toffee.funcov import CovGroup

gr = fc.CovGroup(UT_FCOV("../../../TOFFEE"))

def pred_checker_cover_point(pred_checker):
    g = CovGroup("predChecker addition function")
    # g.add_cover_point(pred_checker.io_out_stage1Out_fixedRange_0, {"io_stage1Out_fixedRange is 0": fc.Eq(0)}, name="stage1Out0 is 0")
       
    # 1.Add point PERD_CHECKER_FIEXEDRANGE to check fixedrange return value:
    #   - bin FIXED_RANGE:      the instruction is need to be fixed
    #   - bin NO_FIXED_RNAGE:   the instruction is not need to be fixed
    def _check_fixedrange(i,value = True):
        def check(pred_checker):
            return (getattr(pred_checker,"io_out_stage1Out_fixedRange_%d"%i)).value == value
        return check
    g.add_watch_point(pred_checker, {
                "FIXED_RANGE_0":  _check_fixedrange(0, True) ,
                }, name = "PERD_CHECKER_FIEXEDRANGE_0", dynamic_bin=True)
    for i in range(15):
        g.add_watch_point(pred_checker, {
                "FIXED_RANGE_%d"%i:  _check_fixedrange(i+1, True) ,
                "NO_FIXED_RANGE_%d"%i: _check_fixedrange(i+1, False),
                }, name = "PERD_CHECKER_FIEXEDRANGE%d"%(i+1), dynamic_bin=True)
        
    # 1.Add point PERD_CHECKER_FIEXEDTAKEN to check fixedrange return value:
    #   - bin FIXED_TAKEN:      the instruction is the first instruction of the FTQ
    #   - bin NO_FIXED_RNAGE:   the instruction is not the first instruction of the FTQ
    def _check_fixedtaken(i,value = True):
        def check(pred_checker):
            return (getattr(pred_checker,"io_out_stage1Out_fixedTaken_%d"%i)).value == value
        return check
    for i in range(16):
        g.add_watch_point(pred_checker, {
                "FIXED_TAKEN_%d"%i:  _check_fixedtaken(i, True) ,
                "NO_FIXED_TAKEN_%d"%i: _check_fixedtaken(i, False),
                }, name = "PERD_CHECKER_FIEXEDTAKEN%d"%i, dynamic_bin=True)
    
    # Reverse mark function coverage to the check point
    def _M(name):
        # get the module name
        return module_name_with(name, "../test_pred_checker")
    
    # - mark PERD_CHECKER_FIEXEDRANGE
    g.mark_function("PERD_CHECKER_FIEXEDRANGE", _M("test_pred_checker_bpu_jal"),bin_name=["FIXED_RANGE_*","NO_FIXED_RANGE_*"],raise_error=False)

    return g
 

@toffee_test.fixture
async def predchecker_env(toffee_request: toffee_test.ToffeeRequest):

    toffee.setup_logging(toffee.WARNING)
    dut = toffee_request.create_dut(DUTPredChecker)
    toffee_request.add_cov_groups(pred_checker_cover_point(dut))
    dut.InitClock("clock")
    toffee.start_clock(dut)
    env = PredCheckerEnv(dut)
    yield env

    import asyncio
    cur_loop = asyncio.get_event_loop()
    for task in asyncio.all_tasks(cur_loop):
        if task.get_name() == "__clock_loop":
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                break