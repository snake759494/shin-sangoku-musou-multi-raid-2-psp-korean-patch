import sys, capstone
b = open(sys.argv[1] if len(sys.argv) > 3 else 'work/iso/PSP_GAME/SYSDIR/BOOT.BIN', 'rb').read()
a, n = int(sys.argv[-2], 16), int(sys.argv[-1], 16)
md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
for i in md.disasm(b[a + 0x74:a + 0x74 + n], a):
    print('%06x: %-8s %s' % (i.address, i.mnemonic, i.op_str))
