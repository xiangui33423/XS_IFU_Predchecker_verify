import toffee_test
from ... import PREDICT_WIDTH, RET_LABEL, RVC_LABEL, BRTYPE_LABEL
from dut.PredChecker import DUTPredChecker
from .pred_checker_dut import predchecker_env
from comm import debug

async def pred_checker(predchecker, ftqvalid, ftqbits, ref_instrRange, ref_instrValid,
                         ref_jumpOffset, ref_pc, ref_pds, target, fire_in=True):
    """ compare the pred_checker result with the reference

    Args:
        pred_checker    (warpper)   : the fixture of the PredChecker
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
    
    async for res in predchecker_env.predCheckerAgent.agent_pred_checker(ftqvalid, ftqbits, 
                                            ref_instrRange, ref_instrValid, ref_jumpOffset, 
                                            ref_pc, ref_pds, target, True):
        if i == 0:
            fixedRange      = res[0]
            fixedTaken      = res[1]
        else:
            fixedTarget     = res[0]
            fixedMissPred   = res[1]
            jalTarget       = res[2]
        i = i + 1

    # define mid-var
    range_fault = [False for i in range(16)]
    jal_fault = [False for i in range(16)]
    jalr_fault = [False for i in range(16)]
    ret_fault = [False for i in range(16)]
    need_fixrange = False
    falut_idx = -1
    ref_fixedTaken = [False for i in range(16)]

    # ====== reference model ======

    # instr Valid Range fix
    for j in range(16):
        ret_fault[j] = ref_pds[j][RET_LABEL] & ref_instrRange[j] & ref_instrValid[j] & (ftqbits > j & ftqvalid | (~ftqvalid))
        jal_fault[j] = (ref_pds[j][BRTYPE_LABEL] == 2) & ref_instrRange[j] & ref_instrValid[j] & (ftqbits > j & ftqvalid | (~ftqvalid))
        jalr_fault[j] = ref_pds[j][BRTYPE_LABEL] == 3 & ref_instrRange[j] & ref_instrValid[j] & (ftqbits > j & ftqvalid | (~ftqvalid))
        if(ret_fault[j] | jal_fault[j] | jalr_fault[j]):
            need_fixrange = True
            falut_idx = j
    if need_fixrange == True:
        for j in range(16):
                ref_fixedRange = False if (j > falut_idx) else True
    else:
        ref_fixedRange = ref_instrRange

    # compare fixed valid range    
    if(ref_fixedRange != fixedRange):
        debug(f"fixedRange error, True Range mask:{ref_fixedRange} Fault Range mas:{fixedRange}") 
        find_error += 1
    
    # TODO: fixed token
    j = 15
    while j >= 0:
        ref_fixedTaken[j] = True if ((ref_fixedRange == True) & ()) else False
        

                

