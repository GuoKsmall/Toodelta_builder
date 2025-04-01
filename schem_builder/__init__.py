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

class SCHEM导入器(Plugin):
    name = "schem导入器"
    author = "Mono"
    version = (0, 0, 1)

    def __init__(self, frame: ToolDelta):
        super().__init__(frame)
        self.frame = frame
        self.game_ctrl = frame.get_game_control()
        self.data = {}
        self.nbtlib = nbtlib
        self.make_data_path()
        self.ListenActive(self.on_inject)
        
    def on_inject(self):
        self.get_x: float | None = None
        self.get_y: float | None = None
        self.get_z: float | None = None
        self.frame.add_console_cmd_trigger(
            ["schem", "导入schem"], None, "导入schem文件", self.dump_schem_menu
        )
        self.frame.add_console_cmd_trigger(
            ["schem-get", "坐标file"], None, "获取schem文件导入坐标", self.get_schem_pos_menu
        )

    def dump_schem_menu(self, _):
        src_path = self.data_path
        if not all((self.get_x, self.get_y, self.get_z)):
            fmts.print_err("未设置导入坐标 (控制台输入 schem-get 以设置)")
            return
        fmts.print_inf(f"文件搜索路径: {src_path}")
        fs = list(filter(lambda x: x.endswith(".schem"), os.listdir(src_path)))
        if fs == []:
            fmts.print_war("该文件夹内没有任何 schem 文件, 无法导入")
            return
        fmts.print_inf("请选择导入的 schem 文件:")
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
        schem_name = schem_file[:-6]
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

    def read_schem(self, file_path: str):
        return self.nbtlib.load(file_path)

    def schem_build(self,name:str,file,x_:int,y_:int,z_:int):
        width = file["Width"]
        height = file["Height"]
        length = file["Length"]
        self.blocks= file["BlockData"]
        Palette= file["Palette"]
        unPalette= {}
        with open(os.path.join(self.data_path,"get.json"),"r",encoding="utf-8") as f:
            data = json.loads(f.read())
        for i,j in Palette.items():
            unPalette[j.real]=i.split(":")[1].split("[")[0]
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
        zero_matrix = np.zeros((16*x_a,height,16*z_a), dtype=int)
        for y in range(height):
            for z in range(length):
                for x in range(width):
                    zero_matrix[x, y, z] = self.blocks[y * width * length + z*width + x]
        self.num = 0
        for z_i in range(z_a):
            for x_i in range(x_a):
                for z in range(16):
                    z=z+16*z_i
                    for x in range(16):
                        x=x+16*x_i
                        for y in range(height):
                            block="air"
                            try:
                                block=data[unPalette[zero_matrix[z,y,x]]]
                            except KeyError:
                                block= "air"
                            if block != "air":
                                self.game_ctrl.sendwocmd(
                                f"setblock {x_+x} {y_+y} {z_+z} {block}"
                                )
                            self.num +=1
                            time.sleep(0.001)
    

    def check_multiple_of_16(self,n):
        if n < 16:
            return 0,0
        else:
            multiple = n // 16  # 计算n是16的几倍
            remainder = n % 16  # 计算n除以16的余数
            return multiple, remainder
entry = plugin_entry(SCHEM导入器)