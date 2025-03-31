import os
import json
from tooldelta import game_utils, plugin_entry, Plugin, ToolDelta, Player, Chat, FrameExit,fmts
from tooldelta.constants import PacketIDS
from tooldelta import utils
packets= PacketIDS
# from rich import print as rp
import numpy as np
import time
import os
import nbtlib


class position:
    def __init__(self, x:int=0, y:int=0, z:int=0):
        self.x=x
        self.y=y
        self.z=z

class file_loader_for_schematic(Plugin):
    name = "schematic导入器"
    author = "Mono"
    version = (0, 0, 1)

    def __init__(self, frame: ToolDelta):
        self.frame = frame
        self.game_ctrl = frame.get_game_control()
        self.data = {}

        self.nbtlib = nbtlib
        
    def on_inject(self):
        self.get_x: float | None = None
        self.get_y: float | None = None
        self.get_z: float | None = None
        self.frame.add_console_cmd_trigger(
            ["schematic", "导入schematic"], None, "导入schematic文件", self.dump_schem_menu
        )
        self.frame.add_console_cmd_trigger(
            ["schematic-get"], None, "获取schematic文件导入坐标", self.get_schem_pos_menu
        )

    def dump_schem_menu(self, _):
        src_path = self.data_path
        if not all((self.get_x, self.get_y, self.get_z)):
            fmts.print_err("未设置导入坐标 (控制台输入 schematic-get 以设置)")
            return
        fmts.print_inf(f"文件搜索路径: {src_path}")
        fs = list(filter(lambda x: x.endswith(".schematic"), os.listdir(src_path)))
        if fs == []:
            fmts.print_war("该文件夹内没有任何 schematic 文件, 无法导入")
            return
        fmts.print_inf("请选择导入的 schematic 文件:")
        for i, j in enumerate(fs):
            fmts.print_inf(f" {i+1} - {j}")
        resp = utils.try_int(input(fmts.fmt_info(f"请选择 (1~{len(fs)}): ")))
        if not resp or resp not in range(1, len(fs) + 1):
            fmts.print_err("输入错, 已退出")
            return
        schem_file = fs[resp - 1]
        self.schem_path = os.path.join(self.data_path, schem_file)
        try:
            schem_inf = self.read_schem(self.schem_path)
        except Exception as err:
            fmts.print_err(f"读取 {schem_file} 出现问题: {err}")
            return
        schem_name = schem_file[:-10]
        fmts.print_inf(f"{schem_name} 的导入已经开始 (进度条显示于游戏内)")
        if self.get_x is None or self.get_y is None or self.get_z is None:
            fmts.print_err("未设置导入坐标, 无法导入")
            return
        utils.createThread(
            self.schem_build,
            (schem_name, schem_inf, int(self.get_x), int(self.get_y), int(self.get_z)),
        )

    def get_schem_pos_menu(self, _):
        avali_players = self.game_ctrl.allplayers
        fmts.print_inf("请选择玩家以获取其坐标:")
        for i, j in enumerate(avali_players):
            fmts.print_inf(f" {i+1} - {j}")
        resp = utils.try_int(
            input(fmts.fmt_info(f"请选择 (1~{len(avali_players)}): "))
        )
        if not resp or resp not in range(1, len(avali_players) + 1):
            fmts.print_err("输入错, 已退出")
            return
        player_get = avali_players[resp - 1]
        self.get_x, self.get_y, self.get_z = game_utils.getPosXYZ(player_get)
        fmts.print_inf(f"成功获取 {player_get} 的坐标.")
    
    def save_for_resumable_import(self):
        if self.get_x is None or self.get_y is None or self.get_z is None:
            fmts.print_err("未设置导入坐标, 无法保存断点续导信息")
            return
        data={
            "名称":"断点续导",
            "路径":self.schem_path,
            "起始坐标":[int(self.get_x), int(self.get_y), int(self.get_z)],
            "方块总数":len(self.blocks),
            "状态": {
                "进度":self.num
                },
        }

        with open(os.path.join(self.data_path,"断点续导.json"),"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=4)

    def read_schem(self, file_path: str):
        return self.nbtlib.load(file_path)

    def schem_build(self,name:str,file,x_:int,y_:int,z_:int):
        width = file["Width"]
        height = file["Height"]
        length = file["Length"]
        print(f"{width} {height} {length}")
        # 遍历所有方块

        self.blocks = file["Blocks"]
        BlockIDs,BlockData = {},{}
        haveBlockData=False
        if "BlockIDs" in file:
            BlockIDs = file["BlockIDs"]
        if "Data" in file:
            BlockData = file["Data"]
            haveBlockData=True

        if BlockIDs == {}:
            with open(os.path.join(self.data_path,"2.json"),"r",encoding="utf-8") as f:
                BlockIDs = json.loads(f.read())
        now_t = 0
        block_p = 0
        


        x_a,x_b= self.check_multiple_of_16(width)
        z_a,z_b= self.check_multiple_of_16(length)

        if x_a>0:
            if x_b!=0:
                x_a=x_a+1
        if z_a>0:
            if z_b!=0:
                z_a=z_a+1
        z_a=z_a+1
        x_a=x_a+1
        total_len = 16*x_a*height*16*z_a
        zero_matrix = np.zeros((16*x_a,height,16*z_a), dtype=int)
        zero_matrix_data = np.zeros((16*x_a,height,16*z_a), dtype=int)
        for y in range(height):
            for z in range(length):
                for x in range(width):
                    zero_matrix[x, y, z] = self.blocks[y * width * length + z*width + x]
                    if haveBlockData:
                        zero_matrix_data[x, y, z] = BlockData[y * width * length + z*width + x]
        self.num = 0
        self.区块 =0
        for z_i in range(z_a):
            for x_i in range(x_a):
                self.区块+=1
                self.game_ctrl.sendwocmd(f"tp {self.game_ctrl.bot_name} {x_+x_i*16} 100 {z_+z_i*16}")
                fmts.print_inf(f"前往{x_+x_i*16} {z_+z_i*16} 区块:{self.区块}/{x_a*z_a}")
                for y in range(height):
                    for x in range(16):
                        x=x+16*x_i
                        for z in range(16):
                            z=z+16*z_i
                            try:
                                block=BlockIDs[str(abs(zero_matrix[x,y,z]))]
                            except KeyError:
                                block="air"
                            if block != "air" and block!="minecraft:air":
                                if haveBlockData:
                                    # print(f"Position(x={x}, y={y}, z={z}): Block= {block} 特殊值 = {zero_matrix_data[x,y,z]}")
                                    block = block + f" {zero_matrix_data[x,y,z]}"
                                else:
                                    ...
                                    # print(f"Position(x={x}, y={y}, z={z}): Block= {block}")
                                self.game_ctrl.sendwocmd(
                                f"setblock {x_+x} {y_+y} {z_+z} {block}"
                                )
                            self.num +=1
                            time.sleep(0.000000001)
                        time.sleep(0.00000001)
                    time.sleep(0.000001)
                            # if time.time() - now_t > 1:
                            #     now_t = time.time()
                            #     bspeed = self.num - block_p
                            #     block_p = self.num
                                # self.progress_bar(name, self.num, total_len, bspeed)
                            # time.sleep(0.003)
                        # self.save_for_resumable_import()

        
    def progress_bar(self, name: str, curr, tota, sped):
        if tota == 0:
            fmts.print_war("总进度为0")
            return
        n = round(curr / tota * 30)
        p = "§b" + "|" * n + "§f" + "|" * (30 - n)
        self.game_ctrl.player_actionbar(
            "@a", f"导入 {name} 进度: §l{curr} §7/ {tota} 速度： {sped}方块每秒 §r\n{p}"
        )
    

    def check_multiple_of_16(self,n):
        if n < 16:
            return 0,0
        else:
            multiple = n // 16  # 计算n是16的几倍
            remainder = n % 16  # 计算n除以16的余数
            return multiple, remainder

    def calculate_chunk_coordinates(self,x, z):
        """
        计算玩家所在区块的起点和终点坐标
        :param x: 玩家的X坐标
        :param z: 玩家的Z坐标
        :return: 区块的起点坐标(x1, z1)和终点坐标(x2, z2)
        """
        # 计算起点坐标
        x1 = (x // 16) * 16
        z1 = (z // 16) * 16
        
        # 计算终点坐标
        x2 = x1 + 15
        z2 = z1 + 15
        
        return x1, z1, x2, z2