# Chase Ripley
# Semester Project
# CS4200 Dr. Zanyar Zohourianshahzadi
# 5/3/2026
#
# ISA Extension, implemented the functionality for mul, mulh, div, and mod instructions in RV32I simulator
# Reused code from Assignment #6, avoided any caching to focus on instruction implementation only
# Added an extra output log to show just the instructions and highlight the M-type instructions added
#
# Also used AI to create a comprehensive input file to test all instructions and edge cases, along with
# an extra file to verify outputs easily from dmem_final.log 



MASK32 = 0xFFFFFFFF
NEGCHECK = 0x80000000 & MASK32 # added to help with sign checking in M-types



# 32-bit helpers
def u32(x):
    return x & MASK32


def s32(x):
    x = x & MASK32
    if x & 0x80000000:
        return x - 0x100000000
    return x


def sign_extend(value, bits):
    mask = (1 << bits) - 1
    v = value & mask
    sign_bit = 1 << (bits - 1)
    if v & sign_bit:
        v = v - (1 << bits)
    return v


def get_bits(x, hi, lo):
    width = hi - lo + 1
    return (x >> lo) & ((1 << width) - 1)



# Immediates
def imm_i(instr):
    return sign_extend(get_bits(instr, 31, 20), 12)


def imm_s(instr):
    hi = get_bits(instr, 31, 25)
    lo = get_bits(instr, 11, 7)
    return sign_extend((hi << 5) | lo, 12)


def imm_b(instr):
    b12 = get_bits(instr, 31, 31)
    b11 = get_bits(instr, 7, 7)
    b10_5 = get_bits(instr, 30, 25)
    b4_1 = get_bits(instr, 11, 8)
    val = (b12 << 12) | (b11 << 11) | (b10_5 << 5) | (b4_1 << 1)
    return sign_extend(val, 13)


def imm_u(instr):
    return get_bits(instr, 31, 12) << 12


def imm_j(instr):
    j20 = get_bits(instr, 31, 31)
    j10_1 = get_bits(instr, 30, 21)
    j11 = get_bits(instr, 20, 20)
    j19_12 = get_bits(instr, 19, 12)
    val = (j20 << 20) | (j19_12 << 12) | (j11 << 11) | (j10_1 << 1)
    return sign_extend(val, 21)



# Decode + control
def decode(instr):
    d = {}
    d["instr"] = u32(instr)
    d["opcode"] = get_bits(instr, 6, 0)
    d["rd"] = get_bits(instr, 11, 7)
    d["funct3"] = get_bits(instr, 14, 12)
    d["rs1"] = get_bits(instr, 19, 15)
    d["rs2"] = get_bits(instr, 24, 20)
    d["funct7"] = get_bits(instr, 31, 25)

    d["imm_I"] = imm_i(instr)
    d["imm_S"] = imm_s(instr)
    d["imm_B"] = imm_b(instr)
    d["imm_U"] = imm_u(instr)
    d["imm_J"] = imm_j(instr)
    return d


def main_control(d):
    op = d["opcode"]
    f3 = d["funct3"]

    c = {
        "RegWrite": 0,
        "MemRead": 0,
        "MemWrite": 0,
        "MemToReg": 0,
        "ALUSrc": 0,
        "Branch": 0,
        "Jump": 0,
        "JumpReg": 0,
        "ALUOp": "ADDR",
        "ImmSel": None,
        "BrType": None,
    }

    if op == 0x33:  # R
        c["RegWrite"] = 1
        c["ALUSrc"] = 0
        c["ALUOp"] = "R"

    elif op == 0x13:  # I-ALU
        c["RegWrite"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "I"
        c["ImmSel"] = "I"

    elif op == 0x03:  # lw
        c["RegWrite"] = 1
        c["MemRead"] = 1
        c["MemToReg"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "ADDR"
        c["ImmSel"] = "I"

    elif op == 0x23:  # sw
        c["MemWrite"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "ADDR"
        c["ImmSel"] = "S"

    elif op == 0x63:  # branches
        c["Branch"] = 1
        c["ALUSrc"] = 0
        c["ALUOp"] = "BR"
        c["ImmSel"] = "B"
        if f3 == 0b000:
            c["BrType"] = "beq"
        elif f3 == 0b001:
            c["BrType"] = "bne"
        elif f3 == 0b100:
            c["BrType"] = "blt"
        elif f3 == 0b101:
            c["BrType"] = "bge"
        elif f3 == 0b110:
            c["BrType"] = "bltu"
        elif f3 == 0b111:
            c["BrType"] = "bgeu"

    elif op == 0x6F:  # jal
        c["Jump"] = 1
        c["RegWrite"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "ADDR"
        c["ImmSel"] = "J"

    elif op == 0x67:  # jalr
        c["Jump"] = 1
        c["JumpReg"] = 1
        c["RegWrite"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "ADDR"
        c["ImmSel"] = "I"

    return c


def select_imm(d, c):
    sel = c["ImmSel"]
    if sel == "I":
        return d["imm_I"]
    if sel == "S":
        return d["imm_S"]
    if sel == "B":
        return d["imm_B"]
    if sel == "U":
        return d["imm_U"]
    if sel == "J":
        return d["imm_J"]
    return 0


def alu_control(c, d):
    op = c["ALUOp"]
    f3 = d["funct3"]
    f7 = d["funct7"]

    if op == "ADDR":
        return "ADD"
    if op == "BR":
        return "SUB"

    if op == "R":
        # --------------------------------------
        # Additional Instructions for Project
        # --------------------------------------
        if f7 == 0b0000001:
            if f3 == 0b000:
                return "MUL"
            if f3 == 0b001:
                return "MULH"
            if f3 == 0b100:
                return "DIV"
            if f3 == 0b110:
                return "MOD"
            
            
        if f3 == 0b000:
            if f7 == 0b0100000: return "SUB"
        if f3 == 0b111:
            return "AND"
        if f3 == 0b110:
            return "OR"
        if f3 == 0b100:
            return "XOR"
        if f3 == 0b001:
            return "SLL"
        if f3 == 0b101:
            return "SRA" if f7 == 0b0100000 else "SRL"
        if f3 == 0b010:
            return "SLT"
        if f3 == 0b011:
            return "SLTU"
        
        return "ADD"

    if op == "I":
        if f3 == 0b000:
            return "ADD"
        if f3 == 0b111:
            return "AND"
        if f3 == 0b110:
            return "OR"
        if f3 == 0b100:
            return "XOR"
        if f3 == 0b010:
            return "SLT"
        if f3 == 0b011:
            return "SLTU"
        if f3 == 0b001:
            return "SLL"
        if f3 == 0b101:
            return "SRA" if f7 == 0b0100000 else "SRL"
        return "ADD"

    return "ADD"


def alu_exec(alu_op, a, b):
    a = u32(a)
    b = u32(b)
    shamt = b & 0x1F

    if alu_op == "ADD":
        return u32(a + b)
    if alu_op == "SUB":
        return u32(a - b)
    if alu_op == "AND":
        return u32(a & b)
    if alu_op == "OR":
        return u32(a | b)
    if alu_op == "XOR":
        return u32(a ^ b)
    if alu_op == "SLL":
        return u32(a << shamt)
    if alu_op == "SRL":
        return u32(a >> shamt)
    if alu_op == "SRA":
        return u32(s32(a) >> shamt)
    if alu_op == "SLT":
        return 1 if s32(a) < s32(b) else 0
    if alu_op == "SLTU":
        return 1 if u32(a) < u32(b) else 0
    
    
    # --------------------------------------
    # Additional Instructions for Project
    # --------------------------------------
    if alu_op == "MUL":
        # Could do result = u32(a*b) & MASK32, since Python can do it that way, but I'm implementing
        # the method we learned in class for more of a challenge
        multiplicand = u32(a) # can use unsigned for regular mul
        multiplier = u32(b)
        result = 0
        
        for _ in range(32): # iterate through all 32 bits
            if multiplier & 1: # check if the LSB is 1
                result = u32(result + multiplicand) # if LSB = 1, add the multiplicand to the result
            multiplicand = u32(multiplicand << 1) # shift the multiplicand left one bit
            multiplier = u32(multiplier >> 1) # shift the multiplier right one bit
            
        return u32(result)
    
    if alu_op == "MULH":
        multiplicand = s32(a) # use signed for upper mul
        multiplier = s32(b)
        result = 0
        sign = True
        
        if multiplicand < 0:
            multiplicand = -multiplicand
            sign = not sign
        if multiplier < 0:
            multiplier = -multiplier
            sign = not sign
        
        # same process as above just using signed
        for _ in range(32):
            if multiplier & 1:
                result = result + multiplicand
            multiplicand = multiplicand << 1
            multiplier = u32(multiplier >> 1)
            
        if not sign:
            result = (~result + 1) & 0xFFFFFFFFFFFFFFFF # 64 bit two's complement
            
        return u32(result >> 32) # shift result right 32 bits for upper half of 64 bit result
        
    if alu_op == "DIV":
        dividend = u32(a) # determine sign outside of calculation
        divisor = u32(b)
        quotient = 0
        remainder = 0
        sign = False # true for pos, false for neg
        
        if divisor == 0: return 0xFFFFFFFF # divide by zero error
        if divisor == -1 and dividend == NEGCHECK: return 0xFFFFFFFF # overflow
        
        if (dividend & NEGCHECK) >> 31 != 0 and (divisor & NEGCHECK) >> 31 != 0:
            sign = True # both negative = positive
            dividend = u32(-s32(dividend)) # make dividend positive for calculation
            divisor = u32(-s32(divisor)) # make divisor positive for calc
            
        if (dividend & NEGCHECK) >> 31 == 0 and (divisor & NEGCHECK) >> 31 == 0:
            sign = True # both positive = positive
            
        # if neither check above switched sign, then the quotient will be negative
        
        # need to compute with positive vals, check both and convert since one may be negative
        if (dividend & NEGCHECK) >> 31 != 0:
            dividend = u32(-s32(dividend))
        if (divisor & NEGCHECK) >> 31 != 0:
            divisor = u32(-s32(divisor))
            
        for i in range(31, -1, -1): # iterate through all bits, using index i for bits in dividend, start from MSB
            remainder = u32(remainder << 1) # shift remainder left
            remainder |= u32(dividend >> i) & 1 # append the ith bit from dividend
        
            if remainder >= u32(divisor): # check if remainder fits in divisor
                remainder -= u32(divisor) # reduce the remainder
                quotient |= u32(1 << i) # append the bit to quotient
         
        # apply the sign to quotient w/ two's complement
        if not sign:
            quotient = (~quotient + 1)
            
        return u32(quotient) # mask to 32-bit regardless of sign
    
    if alu_op == "MOD":
        # can reuse the division algorithm but return remainder, track the sign of the dividend for return
        dividend = u32(a) # determine sign outside of calculation
        divisor = u32(b)
        quotient = 0
        remainder = 0
        sign = True # false = neg, true = pos
        
        if divisor == 0: return u32(dividend) # mod 0 gives remainder = dividend
        
        if (dividend & NEGCHECK) >> 31 != 0:
            dividend = u32(-s32(dividend)) # make dividend positive for calculation
            sign = False # if dividend is negative, result will be negative
        if (divisor & NEGCHECK) >> 31 != 0:
            divisor = u32(-s32(divisor)) # make divisor positive for calc
        
        # same div algo as above, just returning remainder instead
        for i in range(31, -1, -1):
            remainder = u32(remainder << 1)
            remainder |= u32(dividend >> i) & 1
        
            if remainder >= u32(divisor):
                remainder -= u32(divisor)
                quotient |= u32(1 << i)
        
        if not sign: # if negative, two's complement
            remainder = (~remainder + 1)
        
        return u32(remainder) # still mask to 32-bit regardless of sign

    return u32(a + b) # default to add for unknown alu_op

def branch_taken(br_type, rs1_val, rs2_val):
    if br_type == "beq":
        return u32(rs1_val) == u32(rs2_val)
    if br_type == "bne":
        return u32(rs1_val) != u32(rs2_val)
    if br_type == "blt":
        return s32(rs1_val) < s32(rs2_val)
    if br_type == "bge":
        return s32(rs1_val) >= s32(rs2_val)
    if br_type == "bltu":
        return u32(rs1_val) < u32(rs2_val)
    if br_type == "bgeu":
        return u32(rs1_val) >= u32(rs2_val)
    return False



# Stages
def stage_if(pc, imem):
    out = {}
    out["pc"] = u32(pc)
    out["pc_plus4"] = u32(pc + 4)
    out["instr"] = imem.get(u32(pc), None)
    return out


def stage_id(instr, regs):
    d = decode(instr)
    c = main_control(d)
    imm = select_imm(d, c)

    out = {}
    out["d"] = d
    out["c"] = c
    out["imm"] = imm
    out["rs1"] = d["rs1"]
    out["rs2"] = d["rs2"]
    out["rd"] = d["rd"]
    out["rs1_val"] = u32(regs[d["rs1"]])
    out["rs2_val"] = u32(regs[d["rs2"]])
    return out


def stage_ex(pc, pc_plus4, id_out):
    d = id_out["d"]
    c = id_out["c"]
    imm = id_out["imm"]

    rs1_val = id_out["rs1_val"]
    rs2_val = id_out["rs2_val"]

    alu_op = alu_control(c, d)
    alu_in2 = imm if c["ALUSrc"] else rs2_val
    alu_res = alu_exec(alu_op, rs1_val, alu_in2)

    next_pc = u32(pc_plus4)
    taken = False

    if c["Branch"] and c["BrType"] is not None:
        taken = branch_taken(c["BrType"], rs1_val, rs2_val)
        if taken:
            next_pc = u32(pc + imm)

    if c["Jump"]:
        taken = True
        if c["JumpReg"]:
            next_pc = u32((rs1_val + imm) & 0xFFFFFFFE)
        else:
            next_pc = u32(pc + imm)

    out = {}
    out["alu_op"] = alu_op
    out["alu_res"] = u32(alu_res)
    out["next_pc"] = u32(next_pc)
    out["taken"] = taken
    out["pc_plus4"] = u32(pc_plus4)
    out["rs2_val"] = u32(rs2_val)
    return out


def stage_mem(ex_out, id_out, dmem):
    c = id_out["c"]
    
    addr = u32(ex_out["alu_res"])
    mem_data = 0
    
    if c["MemRead"]:
        mem_data = dmem.get(u32(addr), 0)
    
    if c["MemWrite"]:
        dmem[u32(addr)] = u32(ex_out["rs2_val"])
    
    out = {}
    out["addr"] = u32(addr)
    out["mem_data"] = u32(mem_data)
    return out



# Writeback
def stage_wb(pc_plus4, id_out, ex_out, mem_out, regs):
    c = id_out["c"]
    rd = id_out["rd"]

    wb_val = ex_out["alu_res"]
    if c["MemToReg"]:
        wb_val = mem_out["mem_data"]

    if c["Jump"] and c["RegWrite"]:
        wb_val = u32(pc_plus4)

    did_write = False
    if c["RegWrite"] and rd != 0:
        regs[rd] = u32(wb_val)
        did_write = True

    regs[0] = 0

    out = {}
    out["wb_val"] = u32(wb_val)
    out["wb_rd"] = rd
    out["did_write"] = did_write
    return out



# Trace helpers
def try_mnemonic(d):
    op = d["opcode"]
    f3 = d["funct3"]
    f7 = d["funct7"]

    if op == 0x33:
        # --------------------------------------
        # Additional Instructions for Project
        # --------------------------------------
        if f7 == 0b0000001:
            if f3 == 0b000:
                return "mul"
            if f3 == 0b001:
                return "mulh"
            if f3 == 0b100:
                return "div"
            if f3 == 0b110:
                return "mod"
            
            
        if f3 == 0b000:
            return "sub" if f7 == 0b0100000 else "add"
        if f3 == 0b111:
            return "and"
        if f3 == 0b110:
            return "or"
        if f3 == 0b100:
            return "xor"
        if f3 == 0b001:
            return "sll"
        if f3 == 0b101:
            return "sra" if f7 == 0b0100000 else "srl"
        if f3 == 0b010:
            return "slt"
        if f3 == 0b011:
            return "sltu"
        
        return "r?"

    if op == 0x13:
        if f3 == 0b000:
            return "addi"
        if f3 == 0b111:
            return "andi"
        if f3 == 0b110:
            return "ori"
        if f3 == 0b100:
            return "xori"
        if f3 == 0b010:
            return "slti"
        if f3 == 0b011:
            return "sltiu"
        if f3 == 0b001:
            return "slli"
        if f3 == 0b101:
            return "srai" if f7 == 0b0100000 else "srli"
        return "i?"

    if op == 0x03 and f3 == 0b010:
        return "lw"
    if op == 0x23 and f3 == 0b010:
        return "sw"
    if op == 0x63:
        return {
            0b000: "beq",
            0b001: "bne",
            0b100: "blt",
            0b101: "bge",
            0b110: "bltu",
            0b111: "bgeu",
        }.get(f3, "b?")
    if op == 0x6F:
        return "jal"
    if op == 0x67:
        return "jalr"

    return "?"


def trace_line(step, if_out, id_out, ex_out, mem_out, wb_out):
    d = id_out["d"]
    c = id_out["c"]
    mnem = try_mnemonic(d)
    
    parts = []
    parts.append("step=%d" % step)
    parts.append("pc=0x%08X" % if_out["pc"])
    parts.append("instr=0x%08X" % d["instr"])
    parts.append("mn=%s" % mnem)

    parts.append("RegW=%d MemR=%d MemW=%d M2R=%d ALUSrc=%d Br=%d J=%d" % (
        c["RegWrite"], c["MemRead"], c["MemWrite"], c["MemToReg"], c["ALUSrc"], c["Branch"], c["Jump"]
    ))

    parts.append("alu=%s res=0x%08X" % (ex_out["alu_op"], ex_out["alu_res"]))

    if c["MemRead"] or c["MemWrite"]:
        parts.append("mem@0x%08X rdata=0x%08X" % (mem_out["addr"], mem_out["mem_data"]))

    if wb_out["did_write"]:
        parts.append("wb=x%d<-0x%08X" % (wb_out["wb_rd"], wb_out["wb_val"]))

    parts.append("next_pc=0x%08X" % ex_out["next_pc"])
    return " | ".join(parts)


def trace_instruction(id_out):
    d = id_out["d"]
    mnem = try_mnemonic(d)
    string = "0x%08X: %s" % (d["instr"], mnem)
    
    if mnem in ["mul", "mulh", "div", "mod"]:
        string += " <-- New instruction"

    return string



# Loader and log writers
def load_imem_from_file(path):
    imem = {}
    pc = 0
    f = open(path, "r", encoding="utf-8")
    for line in f:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if s.lower().startswith("0x"):
            s = s[2:]
        instr = int(s, 16) & MASK32
        imem[pc] = instr
        pc += 4
    f.close()
    return imem


def write_lines(path, lines):
    f = open(path, "w", encoding="utf-8")
    i = 0
    while i < len(lines):
        f.write(lines[i] + "\n")
        i += 1
    f.close()


def write_regs_log(regs, path):
    f = open(path, "w", encoding="utf-8")
    for i in range(32):
        f.write("x%-2d = 0x%08X (%d)\n" % (i, u32(regs[i]), s32(regs[i])))
    f.close()


def write_dmem_log(dmem, path):
    f = open(path, "w", encoding="utf-8")
    for a in sorted(dmem.keys()):
        f.write("0x%08X : 0x%08X (%d)\n" % (u32(a), u32(dmem[a]), s32(dmem[a])))
    f.close()
    
    
    
# Main
def main():
    imem = load_imem_from_file("input.txt")

    regs = [0] * 32
    dmem = {}  # backing memory (word-addressed dict)

    trace_lines = []
    trace_instructions = []

    pc = 0
    steps = 0
    max_steps = 10_000_000

    while steps < max_steps:
        if_out = stage_if(pc, imem)
        if if_out["instr"] is None:
            break

        pc_plus4 = if_out["pc_plus4"]
        instr = if_out["instr"]

        id_out = stage_id(instr, regs)
        ex_out = stage_ex(if_out["pc"], pc_plus4, id_out)
        mem_out = stage_mem(ex_out, id_out, dmem)
        wb_out = stage_wb(pc_plus4, id_out, ex_out, mem_out, regs)

        trace_lines.append(trace_line(steps, if_out, id_out, ex_out, mem_out, wb_out))
        trace_instructions.append(trace_instruction(id_out))

        pc = u32(ex_out["next_pc"])
        regs[0] = 0
        steps += 1
        
    # write logs
    write_lines("trace.log", trace_lines)
    write_lines("instructions.log", trace_instructions)
    write_regs_log(regs, "regs_final.log")
    write_dmem_log(dmem, "dmem_final.log")

    print("HALT")
    print("steps =", steps)
    print("final pc = 0x%08X" % u32(pc))
    print("wrote trace.log, instructions.log, regs_final.log, dmem_final.log")

if __name__ == "__main__":
    main()
