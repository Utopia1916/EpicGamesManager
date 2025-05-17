import os
import json
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import zipfile
import threading
import time
import sys
from datetime import datetime

class EpicGamesManager:
    def __init__(self):
        # 默认路径
        self.manifests_dir = os.path.join(os.getenv('ProgramData'), 'Epic', 'EpicGamesLauncher', 'Data', 'Manifests')
        self.launcher_installed_path = os.path.join(os.getenv('ProgramData'), 'Epic', 'UnrealEngineLauncher', 'LauncherInstalled.dat')
        
        # 验证路径是否存在
        if not os.path.exists(self.manifests_dir):
            raise FileNotFoundError(f"Manifests目录不存在: {self.manifests_dir}")
        
        if not os.path.exists(self.launcher_installed_path):
            raise FileNotFoundError(f"LauncherInstalled.dat文件不存在: {self.launcher_installed_path}")
        
        # 加载游戏数据
        self.games = self.load_games_data()
    
    def load_games_data(self):
        """加载所有游戏数据，并过滤掉本地不存在的游戏"""
        games = []
        
        # 从LauncherInstalled.dat加载基本信息
        try:
            with open(self.launcher_installed_path, 'r', encoding='utf-8') as f:
                launcher_data = json.load(f)
        except Exception as e:
            raise Exception(f"加载LauncherInstalled.dat失败: {str(e)}")
        
        # 从.item文件加载详细信息
        for item_file in os.listdir(self.manifests_dir):
            if item_file.endswith('.item'):
                item_path = os.path.join(self.manifests_dir, item_file)
                try:
                    with open(item_path, 'r', encoding='utf-8') as f:
                        item_data = json.load(f)
                    
                    # 检查游戏安装目录是否存在
                    install_location = item_data.get('InstallLocation', '')
                    if not os.path.exists(install_location):
                        # 删除不存在的游戏的item文件
                        try:
                            os.remove(item_path)
                            print(f"已删除不存在的游戏配置文件: {item_file}")
                        except Exception as e:
                            print(f"删除配置文件失败: {item_file} - {str(e)}")
                        continue  # 跳过本地不存在的游戏
                    
                    # 匹配LauncherInstalled.dat中的游戏
                    for game in launcher_data.get('InstallationList', []):
                        if (item_data.get('CatalogNamespace') == game.get('NamespaceId') and 
                            item_data.get('CatalogItemId') == game.get('ItemId') and
                            item_data.get('AppName') == game.get('AppName')):
                            
                            # 合并游戏信息
                            merged_game = {
                                'display_name': item_data.get('DisplayName', game.get('AppName', '未知游戏')),
                                'install_location': install_location,
                                'manifest_location': item_data.get('ManifestLocation', ''),
                                'staging_location': item_data.get('StagingLocation', ''),
                                'item_file': item_file,
                                'namespace_id': game.get('NamespaceId'),
                                'item_id': game.get('ItemId'),
                                'app_name': game.get('AppName'),
                                'app_version': game.get('AppVersion'),
                                'artifact_id': game.get('ArtifactId'),
                                'executable': item_data.get('LaunchExecutable', '')
                            }
                            games.append(merged_game)
                            break
                except Exception as e:
                    print(f"加载{item_file}失败: {str(e)}")
                    continue
        
        return games
    
    def migrate_game(self, game_info, new_parent_dir, delete_original=False):
        """
        迁移游戏到新位置
        :param game_info: 游戏信息字典
        :param new_parent_dir: 新的父目录 (如 F:\GAME\EPIC)
        :param delete_original: 是否删除原始文件
        :return: (成功状态, 消息)
        """
        old_location = game_info['install_location']
        game_folder_name = os.path.basename(old_location)
        new_location = os.path.join(new_parent_dir, game_folder_name)
        
        # 1. 检查目标目录是否存在其他游戏
        if os.path.exists(new_parent_dir):
            dir_contents = os.listdir(new_parent_dir)
            if dir_contents and game_folder_name not in dir_contents:
                if not messagebox.askyesno("警告", 
                    f"目标目录 {new_parent_dir} 包含其他文件/文件夹。\n"
                    "继续操作可能会影响其他游戏。\n"
                    "确定要继续吗？"):
                    return False, "迁移已取消"
        
        # 2. 创建父目录
        os.makedirs(new_parent_dir, exist_ok=True)
        
        # 3. 复制游戏文件到新位置
        try:
            if os.path.exists(new_location):
                shutil.rmtree(new_location)
            shutil.copytree(old_location, new_location)
        except Exception as e:
            return False, f"复制游戏文件失败: {str(e)}"
        
        # 4. 更新.item文件
        item_path = os.path.join(self.manifests_dir, game_info['item_file'])
        try:
            with open(item_path, 'r', encoding='utf-8') as f:
                item_data = json.load(f)
            
            # 更新路径
            item_data['InstallLocation'] = new_location
            item_data['ManifestLocation'] = os.path.join(new_location, '.egstore').replace('\\', '/')
            item_data['StagingLocation'] = os.path.join(new_location, '.egstore/bps').replace('\\', '/')
            
            # 备份原文件
            self.backup_file(item_path)
            
            with open(item_path, 'w', encoding='utf-8') as f:
                json.dump(item_data, f, indent=4)
        except Exception as e:
            return False, f"更新.item文件失败: {str(e)}"
        
        # 5. 更新LauncherInstalled.dat
        try:
            # 备份原文件
            self.backup_file(self.launcher_installed_path)
            
            with open(self.launcher_installed_path, 'r', encoding='utf-8') as f:
                launcher_data = json.load(f)
            
            for game in launcher_data['InstallationList']:
                if (game['NamespaceId'] == game_info['namespace_id'] and 
                    game['ItemId'] == game_info['item_id'] and
                    game['AppName'] == game_info['app_name']):
                    game['InstallLocation'] = new_location
                    break
            
            with open(self.launcher_installed_path, 'w', encoding='utf-8') as f:
                json.dump(launcher_data, f, indent=4)
        except Exception as e:
            return False, f"更新LauncherInstalled.dat失败: {str(e)}"
        
        # 6. 可选: 删除原始文件
        if delete_original:
            try:
                shutil.rmtree(old_location)
                return True, f"游戏迁移成功并已删除原始文件! 请重启Epic客户端使更改生效。"
            except Exception as e:
                return True, f"游戏迁移成功，但删除原始文件失败: {str(e)}。请手动删除 {old_location}"
        
        return True, "游戏迁移成功! 请重启Epic客户端使更改生效。原始文件保留在: " + old_location
    
    def backup_file(self, file_path):
        """备份文件到脚本目录的backups文件夹"""
        backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = os.path.basename(file_path)
        backup_path = os.path.join(backup_dir, f"{file_name}.{timestamp}.bak")
        
        try:
            shutil.copy2(file_path, backup_path)
        except Exception as e:
            print(f"备份文件失败: {file_path} -> {backup_path}: {str(e)}")
    
    def backup_game(self, game_info, backup_dir, compress_level=0):
        """
        备份游戏
        :param game_info: 游戏信息字典
        :param backup_dir: 备份目录
        :param compress_level: 压缩级别(0-9)
        :return: (成功状态, 消息)
        """
        try:
            # 准备备份信息
            game_name = game_info['display_name']
            game_location = game_info['install_location']
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{game_name}_{timestamp}"
            backup_path = os.path.join(backup_dir, f"{backup_name}.zip")
            
            # 获取游戏在LauncherInstalled.dat中的条目
            with open(self.launcher_installed_path, 'r', encoding='utf-8') as f:
                launcher_data = json.load(f)
            
            game_entry = None
            for entry in launcher_data['InstallationList']:
                if (entry['NamespaceId'] == game_info['namespace_id'] and 
                    entry['ItemId'] == game_info['item_id'] and
                    entry['AppName'] == game_info['app_name']):
                    game_entry = entry
                    break
            
            if not game_entry:
                return False, "在LauncherInstalled.dat中找不到游戏条目"
            
            # 创建备份zip文件
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. 备份游戏文件
                for root, dirs, files in os.walk(game_location):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('game', os.path.relpath(file_path, game_location))
                        zipf.write(file_path, arcname, compresslevel=compress_level)
                
                # 2. 备份配置文件
                # 2.1 备份.item文件
                item_file_path = os.path.join(self.manifests_dir, game_info['item_file'])
                if os.path.exists(item_file_path):
                    zipf.write(item_file_path, 'config/item_file.item', compresslevel=compress_level)
                
                # 2.2 备份游戏条目
                zipf.writestr('config/game_entry.json', json.dumps(game_entry, indent=4))
                
                # 3. 保存备份元数据
                backup_meta = {
                    'game_name': game_name,
                    'backup_time': timestamp,
                    'original_paths': {
                        'game_location': game_location,
                        'item_file': item_file_path,
                        'launcher_file': self.launcher_installed_path
                    },
                    'game_info': game_info
                }
                zipf.writestr('backup_meta.json', json.dumps(backup_meta, indent=4))
            
            return True, f"备份成功: {backup_path}"
        except Exception as e:
            return False, f"备份失败: {str(e)}"
    
    def restore_game(self, backup_path, restore_location=None):
        """
        恢复游戏
        :param backup_path: 备份文件(.zip)路径
        :param restore_location: 游戏恢复位置(None表示让用户选择)
        :return: (成功状态, 消息)
        """
        try:
            # 读取备份元数据
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                if 'backup_meta.json' not in zipf.namelist():
                    return False, "无效的备份：缺少元数据文件"
                
                with zipf.open('backup_meta.json') as f:
                    backup_meta = json.load(f)
                
                game_info = backup_meta['game_info']
                original_paths = backup_meta['original_paths']
                game_name = game_info['display_name']
                
                # 1. 选择恢复位置
                if not restore_location:
                    suggested_location = os.path.dirname(original_paths['game_location'])
                    restore_location = filedialog.askdirectory(
                        title=f"选择{game_name}的恢复位置",
                        initialdir=suggested_location)
                    if not restore_location:
                        return False, "恢复已取消"
                
                # 2. 准备恢复路径
                game_folder_name = os.path.basename(original_paths['game_location'])
                full_restore_path = os.path.join(restore_location, game_folder_name)
                
                # 3. 创建临时目录
                temp_dir = os.path.join(os.getenv('TEMP'), f"epic_restore_{datetime.now().strftime('%Y%m%d%H%M%S')}")
                os.makedirs(temp_dir, exist_ok=True)
                
                try:
                    # 4. 解压备份文件
                    zipf.extractall(temp_dir)
                    
                    # 5. 恢复游戏文件
                    extracted_game_path = os.path.join(temp_dir, 'game')
                    if os.path.exists(extracted_game_path):
                        if os.path.exists(full_restore_path):
                            shutil.rmtree(full_restore_path)
                        shutil.copytree(extracted_game_path, full_restore_path)
                    
                    # 6. 恢复配置文件
                    # 6.1 恢复.item文件
                    item_temp_path = os.path.join(temp_dir, 'config', 'item_file.item')
                    if os.path.exists(item_temp_path):
                        # 备份原文件
                        self.backup_file(original_paths['item_file'])
                        
                        # 更新.item文件中的路径
                        with open(item_temp_path, 'r', encoding='utf-8') as f:
                            item_data = json.load(f)
                        
                        item_data['InstallLocation'] = full_restore_path
                        item_data['ManifestLocation'] = os.path.join(full_restore_path, '.egstore').replace('\\', '/')
                        item_data['StagingLocation'] = os.path.join(full_restore_path, '.egstore/bps').replace('\\', '/')
                        
                        os.makedirs(self.manifests_dir, exist_ok=True)
                        with open(original_paths['item_file'], 'w', encoding='utf-8') as f:
                            json.dump(item_data, f, indent=4)
                    
                    # 6.2 恢复游戏条目
                    entry_temp_path = os.path.join(temp_dir, 'config', 'game_entry.json')
                    if os.path.exists(entry_temp_path):
                        with open(entry_temp_path, 'r', encoding='utf-8') as f:
                            game_entry = json.load(f)
                        
                        # 更新安装路径
                        game_entry['InstallLocation'] = full_restore_path.replace('\\', '/')
                        
                        # 备份原文件
                        self.backup_file(self.launcher_installed_path)
                        
                        # 加载当前LauncherInstalled.dat
                        if os.path.exists(self.launcher_installed_path):
                            with open(self.launcher_installed_path, 'r', encoding='utf-8') as f:
                                launcher_data = json.load(f)
                        else:
                            launcher_data = {'InstallationList': []}
                        
                        # 检查是否已存在相同游戏
                        exists = False
                        for i, entry in enumerate(launcher_data['InstallationList']):
                            if (entry['NamespaceId'] == game_entry['NamespaceId'] and
                                entry['ItemId'] == game_entry['ItemId'] and
                                entry['AppName'] == game_entry['AppName']):
                                # 更新现有条目
                                launcher_data['InstallationList'][i] = game_entry
                                exists = True
                                break
                        
                        if not exists:
                            # 添加到列表末尾
                            launcher_data['InstallationList'].append(game_entry)
                        
                        # 保存更新
                        os.makedirs(os.path.dirname(self.launcher_installed_path), exist_ok=True)
                        with open(self.launcher_installed_path, 'w', encoding='utf-8') as f:
                            json.dump(launcher_data, f, indent=4)
                finally:
                    # 清理临时目录
                    shutil.rmtree(temp_dir, ignore_errors=True)
            
            return True, f"游戏恢复成功到: {full_restore_path}"
        except Exception as e:
            return False, f"恢复失败: {str(e)}"
    
    def uninstall_game(self, game_info):
        """
        卸载游戏
        :param game_info: 游戏信息字典
        :return: (成功状态, 消息)
        """
        try:
            # 1. 删除游戏文件
            game_location = game_info['install_location']
            if os.path.exists(game_location):
                shutil.rmtree(game_location)
            
            # 2. 删除.item文件
            item_file_path = os.path.join(self.manifests_dir, game_info['item_file'])
            if os.path.exists(item_file_path):
                # 备份原文件
                self.backup_file(item_file_path)
                os.remove(item_file_path)
            
            # 3. 从LauncherInstalled.dat中移除游戏条目
            # 备份原文件
            self.backup_file(self.launcher_installed_path)
            
            with open(self.launcher_installed_path, 'r', encoding='utf-8') as f:
                launcher_data = json.load(f)
            
            # 查找并移除游戏条目
            new_installation_list = [
                entry for entry in launcher_data['InstallationList']
                if not (entry['NamespaceId'] == game_info['namespace_id'] and
                       entry['ItemId'] == game_info['item_id'] and
                       entry['AppName'] == game_info['app_name'])
            ]
            
            launcher_data['InstallationList'] = new_installation_list
            
            with open(self.launcher_installed_path, 'w', encoding='utf-8') as f:
                json.dump(launcher_data, f, indent=4)
            
            return True, f"游戏卸载成功: {game_info['display_name']}"
        except Exception as e:
            return False, f"卸载失败: {str(e)}"

class EpicGamesManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Epic Games 游戏管理器")
        self.root.geometry("800x600")
        
        # 初始化管理器
        try:
            self.manager = EpicGamesManager()
        except Exception as e:
            messagebox.showerror("错误", f"初始化失败: {str(e)}")
            self.root.destroy()
            return
        
        # 创建UI元素
        self.create_widgets()
        
        # 加载游戏列表
        self.refresh_game_list()
    
    def create_widgets(self):
        """创建UI元素"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 游戏列表
        self.game_list_frame = ttk.LabelFrame(main_frame, text="已安装的游戏")
        self.game_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 游戏列表树状视图
        self.tree = ttk.Treeview(self.game_list_frame, columns=('name', 'version', 'location', 'executable'), show='headings')
        self.tree.heading('name', text='游戏名称')
        self.tree.heading('version', text='版本')
        self.tree.heading('location', text='安装位置')
        self.tree.heading('executable', text='可执行文件')
        
        self.tree.column('name', width=200)
        self.tree.column('version', width=100)
        self.tree.column('location', width=300)
        self.tree.column('executable', width=150)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 迁移按钮
        migrate_btn = ttk.Button(button_frame, text="迁移游戏", command=self.migrate_game)
        migrate_btn.pack(side=tk.LEFT, padx=5)
        
        # 备份按钮
        backup_btn = ttk.Button(button_frame, text="备份游戏", command=self.backup_game)
        backup_btn.pack(side=tk.LEFT, padx=5)
        
        # 恢复按钮
        restore_btn = ttk.Button(button_frame, text="恢复游戏", command=self.restore_game)
        restore_btn.pack(side=tk.LEFT, padx=5)
        
        # 卸载按钮
        uninstall_btn = ttk.Button(button_frame, text="卸载游戏", command=self.uninstall_game)
        uninstall_btn.pack(side=tk.LEFT, padx=5)
        
        # 刷新按钮
        refresh_btn = ttk.Button(button_frame, text="刷新列表", command=self.refresh_game_list)
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def refresh_game_list(self):
        """刷新游戏列表"""
        self.tree.delete(*self.tree.get_children())
        for game in self.manager.games:
            self.tree.insert('', 'end', values=(
                game['display_name'],
                game['app_version'],
                game['install_location'],
                game['executable']
            ))
        self.status_var.set(f"找到 {len(self.manager.games)} 个游戏")
    
    def get_selected_game(self):
        """获取选中的游戏"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个游戏")
            return None
        
        item = self.tree.item(selection[0])
        game_name = item['values'][0]
        
        for game in self.manager.games:
            if game['display_name'] == game_name:
                return game
        
        return None
    
    def migrate_game(self):
        """迁移游戏"""
        game = self.get_selected_game()
        if not game:
            return
        
        # 选择目标目录
        default_dir = os.path.dirname(game['install_location'])
        new_parent_dir = filedialog.askdirectory(
            title="选择新的游戏父目录",
            initialdir=default_dir
        )
        
        if not new_parent_dir:
            return
        
        # 询问是否删除原始文件
        delete_original = messagebox.askyesno("确认", "迁移完成后删除原始文件?")
        
        # 执行迁移
        self.status_var.set(f"正在迁移 {game['display_name']}...")
        self.root.update()
        
        success, message = self.manager.migrate_game(game, new_parent_dir, delete_original)
        
        if success:
            messagebox.showinfo("成功", message)
            self.refresh_game_list()
        else:
            messagebox.showerror("错误", message)
        
        self.status_var.set(message)
    
    def backup_game(self):
        """备份游戏"""
        game = self.get_selected_game()
        if not game:
            return
        
        # 选择备份目录
        backup_dir = filedialog.askdirectory(
            title="选择备份保存位置",
            initialdir=os.path.expanduser("~\\Desktop")
        )
        
        if not backup_dir:
            return
        
        # 询问压缩级别
        compress_level = simpledialog.askinteger(
            "压缩级别",
            "输入压缩级别 (0-9, 0=不压缩, 9=最大压缩):",
            minvalue=0, maxvalue=9, initialvalue=0
        )
        
        if compress_level is None:
            return
        
        # 执行备份
        self.status_var.set(f"正在备份 {game['display_name']}...")
        self.root.update()
        
        success, message = self.manager.backup_game(game, backup_dir, compress_level)
        
        if success:
            messagebox.showinfo("成功", message)
        else:
            messagebox.showerror("错误", message)
        
        self.status_var.set(message)
    
    def restore_game(self):
        """恢复游戏"""
        # 选择备份文件
        backup_file = filedialog.askopenfilename(
            title="选择备份文件",
            filetypes=[("ZIP 备份文件", "*.zip")],
            initialdir=os.path.expanduser("~\\Desktop")
        )
        
        if not backup_file:
            return
        
        # 执行恢复
        self.status_var.set("正在恢复游戏...")
        self.root.update()
        
        success, message = self.manager.restore_game(backup_file)
        
        if success:
            messagebox.showinfo("成功", message)
            self.refresh_game_list()
        else:
            messagebox.showerror("错误", message)
        
        self.status_var.set(message)
    
    def uninstall_game(self):
        """卸载游戏"""
        game = self.get_selected_game()
        if not game:
            return
        
        # 确认卸载
        if not messagebox.askyesno("确认", f"确定要卸载 {game['display_name']} 吗?"):
            return
        
        # 执行卸载
        self.status_var.set(f"正在卸载 {game['display_name']}...")
        self.root.update()
        
        success, message = self.manager.uninstall_game(game)
        
        if success:
            messagebox.showinfo("成功", message)
            self.refresh_game_list()
        else:
            messagebox.showerror("错误", message)
        
        self.status_var.set(message)

def main():
    root = tk.Tk()
    try:
        app = EpicGamesManagerGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("错误", f"程序发生错误: {str(e)}")
        root.destroy()

if __name__ == "__main__":
    main()
