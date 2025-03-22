import toffee_test
from ... import PREDICT_WIDTH, RET_LABEL, RVC_LABEL, BRTYPE_LABEL
from dut.PredChecker import DUTPredChecker
from .pred_checker_dut import *
from comm import TAG_LONG_TIME_RUN, TAG_SMOKE, TAG_RARELY_USED, debug
import pytest
from ..env import PredCheckerEnv

async def pred_check(predchecker, ftqvalid, ftqbits, ref_instrRange, ref_instrValid,
                         ref_jumpOffset, ref_pc, ref_pds, target, fire_in=True):
    """ compare the pred_checker result with the reference

    Args:
        pred_checker    (wartestcaseper)   : the fixture of the PredChecker
        ftqvalid        (bool)      : Predict the existence of jump instr(JAL) for ftq
        ftqbits         (int)       : num of jump instr for ftq
        ref_instrRange  (list[bool]): the list of whether the instr is within the valid instr range of ftq
        ref_instrValid  (list[bool]): the list of whether it is a valid instr
        ref_jumpOffset  (list[int]) : the list of the jump target for this instr 
        ref_pc          (list[int]) : pc list
        ref_pds         (list[map]) : the list of pre-decode message
        target          (int)       : the start addr of next ftq
    """
    find_error = 0
    i = 0
    
    async for res in predchecker.agent_pred_check(ftqvalid, ftqbits, 
                                            ref_instrRange, ref_instrValid, ref_jumpOffset, 
                                            ref_pc, ref_pds, target, True):
        if i == 0:
            fixedRange      = res[0]
            fixedTaken      = res[1]
        elif i == 1:
            fixedTarget     = res[0]
            fixedMissPred   = res[1]
            jalTarget       = res[2]
        i = i + 1

    # define mid-var
    range_fault = [False for i in range(16)]
    jal_fault = [False for i in range(16)]
    jalr_fault = [False for i in range(16)]
    ret_fault = [False for i in range(16)]
    target_fault = [False for i in range(16)]
    need_fixrange = False
    falut_idx = -1
    jumpTargets = [0 for i in range(16)]
    CFITaken_NOT = [0 for i in range(16)]
    invalidTaken = [0 for i in range(16)]
    # ref result initialize
    ref_fixedTaken = [False for i in range(16)]
    ref_fixedRange = [False for i in range(16)]
    ref_fixedMissPred = [False for i in range(16)]
    ref_target = [0 for i in range(16)]

    if i == 0:
    # ====== reference model ======
    # instr Valid Range is needed to fix
        for j in range(16):
            ret_fault[j]  = ref_pds[j][RET_LABEL] and ref_instrRange[j] and ref_instrValid[j] and (ftqbits > j & ftqvalid or (~ftqvalid))
            jal_fault[j]  = (ref_pds[j][BRTYPE_LABEL] == 2) and ref_instrRange[j] and ref_instrValid[j] and (ftqbits > j & ftqvalid or (~ftqvalid))
            jalr_fault[j] = (ref_pds[j][BRTYPE_LABEL] == 3) and (not ref_pds[j][RET_LABEL]) and ref_instrRange[j] and ref_instrValid[j] & (ftqbits > j & ftqvalid or (~ftqvalid))
            if(ret_fault[j] | jal_fault[j] | jalr_fault[j]):
                need_fixrange = True
                falut_idx = j
        if need_fixrange == True:
            for j in range(16):
                    ref_fixedRange[j] = False if (j > falut_idx) else True
        else:
            ref_fixedRange = ref_instrRange

        # compare fixed valid range    
        if(ref_fixedRange != fixedRange):
            debug(f"fixedRange error, True Range mask:{ref_fixedRange} Fault Range is:{fixedRange}") 
            find_error += 1

        # whether the instr is first CFI
        j = 15
        while j >= 0:
            ref_fixedTaken[j] = True if ((ref_fixedRange == True) & (ref_instrValid) & ftqvalid                         # instr is valid, 
                                                                                                                        # because first CFI's fixedRange must be ture, 
                                                                                                                        # the others must be false
                                        & ((ref_pds[j][BRTYPE_LABEL] == 2) or ref_pds[j][RET_LABEL] or (ftqbits == j))  # whether instr is CFI
                                        ) else False

        # compare fixedtaken
        if(ref_fixedTaken != fixedTaken):
            debug(f"fixedTaken error, True fixedTaken is :{ref_fixedTaken} Fault Range is:{fixedTaken}") 
            find_error += 1

    elif i == 1:
        # check predecode error
        for j in range(16):       
            jumpTargets[j] = ref_pc[j] + ref_jumpOffset[j]    
            target_fault[j] = (ref_fixedRange[j] and ref_instrValid[j] and # instr valid   
                            (ref_pds[j][BRTYPE_LABEL] == 2 or ref_pds[j][BRTYPE_LABEL] == 1) and ftqvalid and (ftqbits == j) # jump instr 
                            and (target[j] != jumpTargets[j])) # target fault 
            CFITaken_NOT[j] = ref_fixedRange[j] and (ref_instrValid[j]) and (ftqbits == j) and (ref_pds[j][BRTYPE_LABEL] != 0) and ftqvalid
            invalidTaken[j] = ref_fixedRange[j] and (not ref_instrValid[j]) and (ftqbits == j) and ftqvalid
            ref_fixedMissPred[j] = jal_fault[j] or jalr_fault[j] or ret_fault[j] or target_fault[j] or CFITaken_NOT[j] or invalidTaken[j]
        # compare fixedMissPred
        if(ref_fixedMissPred != fixedMissPred):
            debug(f"fixedMissPred error, True fixedMissPred is :{ref_fixedMissPred} Fault fixedMissPred is:{fixedMissPred}") 
            find_error += 1

        # TODO: fixed Target
        # for j in range(16):
        #     ref_fixedTarget[j] = 

        # jalTarget
        for j in range(16):
            ref_target[j] = jumpTargets[j]
        # compare jalTarget
        if(ref_target != target):
            debug(f"target error, True target is :{ref_target} Fault target is:{target}") 
            find_error += 1
        
@pytest.mark.toffe_tags(TAG_SMOKE)
@toffee_test.testcase
async def test_predchecker_smoke(predchecker_env: PredCheckerEnv):
    fvalid = False
    bits = 0
    jumpOffset = [0 for i in range(PREDICT_WIDTH)]
    instrRange = [True for i in range(PREDICT_WIDTH)]
    instrValid = [True for i in range(PREDICT_WIDTH)] # all RVCs
    pc = [0 for i in range(PREDICT_WIDTH)]
    pds = [{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 } for i in range(PREDICT_WIDTH)]
    tgt = 0
    await pred_check(predchecker_env.predCheckerAgent,fvalid, bits, instrRange, instrValid, jumpOffset, pc, pds, tgt)


N = 10
T = 1 << 16
@pytest.mark.toffee_tags(TAG_LONG_TIME_RUN)
@toffee_test.testcase
async def test_pred_checker_bpu_jal_1_1(predchecker_env: PredCheckerEnv):
    covered = -1
    # gr.add_watch_point(predchecker_env,{

    #                 }, name= "PRED_CHECKER_BPU_JAL")
    # gr.mark_function("PRED_CHECKER_BPU_JAL", test_pred_checker_bpu_jal)
    pc = [0 for i in range(PREDICT_WIDTH)]
    fvalid = False
    bits = 0
    jumpOffset = [0 for i in range(PREDICT_WIDTH)]
    instrRange = [True for i in range(PREDICT_WIDTH)]
    instrValid = [True for i in range(PREDICT_WIDTH)]
    pds = [{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 } for i in range(PREDICT_WIDTH)]
    tgt = 0
    await pred_check(predchecker_env.predCheckerAgent,fvalid, bits, instrRange, instrValid, jumpOffset, pc, pds, tgt)

@pytest.mark.toffee_tags(TAG_LONG_TIME_RUN)
@toffee_test.testcase
async def test_pred_checker_bpu_jal_1_2(predchecker_env: PredCheckerEnv):
    pc = [0 for i in range(PREDICT_WIDTH)]
    fvalid = True
    bits = 0
    jumpOffset = [0 for i in range(PREDICT_WIDTH)]
    instrRange = [True]+[False for i in range(PREDICT_WIDTH-1)]
    instrValid = [True for i in range(PREDICT_WIDTH)]
    pds = [{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 }]+[{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 } for i in range(PREDICT_WIDTH-1)]
    tgt=0
    await pred_check(predchecker_env.predCheckerAgent,fvalid, bits, instrRange, instrValid, jumpOffset, pc, pds, tgt)

@pytest.mark.toffee_tags(TAG_LONG_TIME_RUN)
@toffee_test.testcase
async def test_pred_checker_bpu_jal_2_1(predchecker_env: PredCheckerEnv):
    pc = [0 for i in range(PREDICT_WIDTH)]
    fvalid = False
    bits = 0
    jumpOffset = [0 for i in range(PREDICT_WIDTH)]
    instrRange = [True]+[False for i in range(PREDICT_WIDTH-1)]
    instrValid = [True for i in range(PREDICT_WIDTH)]
    pds = [{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 }]+[{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 } for i in range(PREDICT_WIDTH-1)]
    tgt=0
    await pred_check(predchecker_env.predCheckerAgent,fvalid, bits, instrRange, instrValid, jumpOffset, pc, pds, tgt)

@pytest.mark.toffee_tags(TAG_LONG_TIME_RUN)
@toffee_test.testcase
async def test_pred_checker_bpu_jal_2_2(predchecker_env: PredCheckerEnv):
    pc = [0 for i in range(PREDICT_WIDTH)]
    fvalid = True
    bits = 2
    jumpOffset = [0 for i in range(PREDICT_WIDTH)]
    instrRange = [True,True,True]+[False for i in range(PREDICT_WIDTH-3)]
    instrValid = [True for i in range(PREDICT_WIDTH)]
    pds = [{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 } for i in range(3)]+[{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 } for i in range(PREDICT_WIDTH-3)]
    tgt=0
    await pred_check(predchecker_env.predCheckerAgent,fvalid, bits, instrRange, instrValid, jumpOffset, pc, pds, tgt)

@pytest.mark.toffee_tags(TAG_LONG_TIME_RUN)
@toffee_test.testcase
async def test_pred_checker_bpu_ret_1_1(predchecker_env: PredCheckerEnv):
    pc = [0 for i in range(PREDICT_WIDTH)]
    fvalid = False
    bits = 0
    jumpOffset = [0 for i in range(PREDICT_WIDTH)]
    instrRange = [True for i in range(PREDICT_WIDTH)]
    instrValid = [True for i in range(PREDICT_WIDTH)]
    pds = [{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 } for i in range(PREDICT_WIDTH)]
    tgt = 0
    await pred_check(predchecker_env.predCheckerAgent,fvalid, bits, instrRange, instrValid, jumpOffset, pc, pds, tgt)

@pytest.mark.toffee_tags(TAG_LONG_TIME_RUN)
@toffee_test.testcase
async def test_pred_checker_bpu_ret_1_2(predchecker_env: PredCheckerEnv):
    for j in range(16):
        pc = [0 for i in range(PREDICT_WIDTH)]
        fvalid = True
        bits = j
        jumpOffset = [0 for i in range(PREDICT_WIDTH)]
        instrRange = [True for i in range(j+1)] + [False for i in range(PREDICT_WIDTH-1-j)]
        instrValid = [True for i in range(PREDICT_WIDTH)]
        pds = [{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 1 } for i in range(j+1)]+[{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 } for i in range(PREDICT_WIDTH-1-j)]
        tgt = 0
        await pred_check(predchecker_env.predCheckerAgent,fvalid, bits, instrRange, instrValid, jumpOffset, pc, pds, tgt)

@pytest.mark.toffee_tags(TAG_LONG_TIME_RUN)
@toffee_test.testcase
async def test_pred_checker_bpu_ret_2_1(predchecker_env: PredCheckerEnv):
    pc = [0 for i in range(PREDICT_WIDTH)]
    fvalid = False
    bits = 0
    j = 0
    jumpOffset = [0 for i in range(PREDICT_WIDTH)]
    instrRange = [True for i in range(j+1)] + [False for i in range(PREDICT_WIDTH-1-j)]
    instrValid = [True for i in range(PREDICT_WIDTH)]
    pds = [{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 1 } for i in range(j+1)]+[{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 } for i in range(PREDICT_WIDTH-1-j)]
    tgt = 0
    await pred_check(predchecker_env.predCheckerAgent,fvalid, bits, instrRange, instrValid, jumpOffset, pc, pds, tgt)

@pytest.mark.toffee_tags(TAG_LONG_TIME_RUN)
@toffee_test.testcase
async def test_pred_checker_bpu_ret_2_2(predchecker_env: PredCheckerEnv):
    for j in range(16):
        pc = [0 for i in range(PREDICT_WIDTH)]
        fvalid = False
        bits = 0
        jumpOffset = [0 for i in range(PREDICT_WIDTH)]
        instrRange = [True for i in range(j+1)] + [False for i in range(PREDICT_WIDTH-1-j)]
        instrValid = [True for i in range(PREDICT_WIDTH)]
        pds = [{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 1 } for i in range(j+1)]+[{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 } for i in range(PREDICT_WIDTH-1-j)]
        tgt = 0
        await pred_check(predchecker_env.predCheckerAgent,fvalid, bits, instrRange, instrValid, jumpOffset, pc, pds, tgt)

@pytest.mark.toffee_tags(TAG_LONG_TIME_RUN)
@toffee_test.testcase
async def test_pred_checker_bpu_jal_3_1(predchecker_env: PredCheckerEnv):
    pc = [0 for i in range(PREDICT_WIDTH)]
    fvalid = False
    bits = 0
    jumpOffset = [0 for i in range(PREDICT_WIDTH)]
    instrRange = [True]+[False for i in range(PREDICT_WIDTH-1)]
    instrValid = [True for i in range(PREDICT_WIDTH)]
    pds = [{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 }]+[{RVC_LABEL: True, RET_LABEL: False, BRTYPE_LABEL: 0 } for i in range(PREDICT_WIDTH-1)]
    tgt=0
    await pred_check(predchecker_env.predCheckerAgent,fvalid, bits, instrRange, instrValid, jumpOffset, pc, pds, tgt)
