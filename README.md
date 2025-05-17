# Epic Games Manager(E宝游戏管理器)
## Only Chinese, No other localizations yet
### 警告，完全由AI DeepSeek编写
任意目录均可执行

脚本运行目录备份的是每次执行功能前的配置文件，至于配置文件是什么请往下看，一般来说用不上，如果出现意外情况导致EPIC上显示游戏未安装再往下读
目前没有进度条显示，后续可能会添加吧
我暂时没发现问题，如有问题请报告，如有想要的功能也请报告
(只要不在执行动作时关闭窗口或关掉电脑，基本不会有问题)

提供py脚本源文件以及exe程序(使用auto-py-to-exe自动转换，理论上来说不需要py环境，但我无法进行测试，原因是显而易见的)

Epic games安装的游戏以及相关的记录说明：
在游戏目录下都有一个名为《.egstore》的文件夹

其中有《.mancpn》和《.manifest》两个不同后缀的文件，两个文件的文件名都是相同的字符串，代表了游戏的ID

此ID则与《C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests》目录下的《.item》一一对应

每安装一个游戏，此处则应该包含一个《.item》文件

《.item》文件可以文本形式打开，其中记录有游戏的安装信息，格式为：
{
	"FormatVersion": 0,
	"bIsIncompleteInstall": false,
	"LaunchCommand": "",
	"LaunchExecutable": "MovingOut.exe",
	"ManifestLocation": "E:\\GAME\\EPIC\\MovingOut/.egstore",
	……(此处为省略)
	"DisplayName": "Moving Out",
	"InstallationGuid": "06CB9020464B048975A7698E941F202D",
	"InstallLocation": "E:\\GAME\\EPIC\\MovingOut",
	……(此处为省略)	
	"StagingLocation": "E:\\GAME\\EPIC\\MovingOut/.egstore/bps",
	……(此处为省略)
}
其中值《ManifestLocation》、《StagingLocation》与《InstallLocation》值均与游戏的安装位置有关

此外，在目录《C:\ProgramData\Epic\UnrealEngineLauncher》中有一个《LauncherInstalled.dat》文件
同样可以文本形式打开，其中同样记录了每个游戏的安装信息，格式为：

{
	"InstallationList": [
		{
			"InstallLocation": "E:\\GAME\\EPIC\\MovingOut",
			"NamespaceId": "f919a1262081444fb28f0fdef68d6b14",
			"ItemId": "ad66ba38abed4035917aab1b1a3a3607",
			"ArtifactId": "8e29583ae4b44a21883038668f7e301e",
			"AppVersion": "11",
			"AppName": "8e29583ae4b44a21883038668f7e301e"
		},
		{
			"InstallLocation": "F:\\GAME\\EPIC\\ShadowTactics",
			"NamespaceId": "2f215955790d456b80c291bc2feaf7f7",
			"ItemId": "c275c2a3a6564d298db3dd4ca623e1f9",
			"ArtifactId": "Fangtooth",
			"AppVersion": "2.2.11.F.Windows_EpicStore.2023_01_17_1555_Windows",
			"AppName": "Fangtooth"
		}
	]
}

要迁移游戏，将游戏目录整个复制到想要迁移的目录
此处以《MovingOut》举例

打开《C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests》目录，逐个查看《.item》文件，确认游戏《MovingOut》所处位置，找到后格式如下：
"ManifestLocation": "E:\\GAME\\EPIC\\MovingOut/.egstore",
"InstallLocation": "E:\\GAME\\EPIC\\MovingOut",
"StagingLocation": "E:\\GAME\\EPIC\\MovingOut/.egstore/bps",
备注：《E:\\GAME\\EPIC\\MovingOut/.egstore》在资源管理器中代表：《E:\GAME\EPIC\MovingOut\.egstore》
按照格式修改目录为迁移目标
随后打开《C:\ProgramData\Epic\UnrealEngineLauncher》目录，打开《LauncherInstalled.dat》文件
修改其中的：《InstallLocation》后的目录为迁移目标
最后重启EPIC客户端
