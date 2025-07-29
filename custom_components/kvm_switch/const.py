DOMAIN = "kvm_switch"
DEFAULT_NAME = "KVM Switch"
DEFAULT_HOST = "10.0.0.10"
DEFAULT_PORT = 1110
DEFAULT_OUTPUT_PORTS = 4

# 指令映射 - 按照实际协议修正
COMMAND_MAP = {
    # OUT1 控制指令
    "OUT1_IN1": "6369722030300D0A",  # cir 00

    "OUT1_IN2": "6369722030310D0A",  # cir 01

    "OUT1_IN3": "6369722030320D0A",  # cir 02

    "OUT1_IN4": "6369722030330D0A",  # cir 03

    "OUT1_PLUS": "6369722031650D0A",  # cir 1e

    "OUT1_MINUS": "6369722031640D0A", # cir 1d


    # OUT2 控制指令
    "OUT2_IN1": "6369722030380D0A",  # cir 08

    "OUT2_IN2": "6369722030390D0A",  # cir 09

    "OUT2_IN3": "6369722030610D0A",  # cir 0a

    "OUT2_IN4": "6369722030620D0A",  # cir 0b

    "OUT2_PLUS": "6369722030360D0A",  # cir 06

    "OUT2_MINUS": "6369722030350D0A", # cir 05


    # OUT3 控制指令
    "OUT3_IN1": "6369722031300D0A",  # cir 10

    "OUT3_IN2": "6369722031310D0A",  # cir 11

    "OUT3_IN3": "6369722031320D0A",  # cir 12

    "OUT3_IN4": "6369722031330D0A",  # cir 13

    "OUT3_PLUS": "6369722030650D0A",  # cir 0e

    "OUT3_MINUS": "6369722030640D0A", # cir 0d


    # OUT4 控制指令
    "OUT4_IN1": "6369722031380D0A",  # cir 18

    "OUT4_IN2": "6369722031390D0A",  # cir 19

    "OUT4_IN3": "6369722031610D0A",  # cir 1a

    "OUT4_IN4": "6369722031620D0A",  # cir 1b

    "OUT4_PLUS": "6369722031360D0A",  # cir 16

    "OUT4_MINUS": "6369722031350D0A", # cir 15

}

# 状态映射 - 标准化为IN1-IN4
STATE_MAP = {
    # OUT1 状态
    "s10": "IN1",
    "s11": "IN2",
    "s12": "IN3",
    "s13": "IN4",
    # OUT2 状态
    "s20": "IN1",
    "s21": "IN2",
    "s22": "IN3",
    "s23": "IN4",
    # OUT3 状态
    "s30": "IN1",
    "s31": "IN2",
    "s32": "IN3",
    "s33": "IN4",
    # OUT4 状态
    "s40": "IN1",
    "s41": "IN2",
    "s42": "IN3",
    "s43": "IN4",
}