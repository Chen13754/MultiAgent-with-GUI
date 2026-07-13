using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("Multiagent Studio Launcher")]
[assembly: AssemblyDescription("Starts the packaged Multiagent Studio desktop application")]
[assembly: AssemblyCompany("Multiagent Studio")]
[assembly: AssemblyProduct("Multiagent Studio")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

internal static class MultiagentStudioLauncher
{
    [STAThread]
    private static void Main()
    {
        string launcherDirectory = AppDomain.CurrentDomain.BaseDirectory;
        string[] candidates =
        {
            Path.Combine(launcherDirectory, "dist", "MultiagentStudio", "MultiagentStudio.exe"),
            Path.Combine(launcherDirectory, "MultiagentStudio", "MultiagentStudio.exe")
        };

        string target = null;
        foreach (string candidate in candidates)
        {
            if (File.Exists(candidate))
            {
                target = Path.GetFullPath(candidate);
                break;
            }
        }

        if (target == null)
        {
            MessageBox.Show(
                "找不到正式桌面程序。\r\n\r\n请确认以下文件存在：\r\n"
                    + candidates[0]
                    + "\r\n\r\n如果尚未构建，请先生成桌面发行包。",
                "Multiagent Studio 无法启动",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
            return;
        }

        try
        {
            Process.Start(
                new ProcessStartInfo
                {
                    FileName = target,
                    WorkingDirectory = Path.GetDirectoryName(target),
                    UseShellExecute = true
                }
            );
        }
        catch (Exception error)
        {
            MessageBox.Show(
                "启动 Multiagent Studio 失败。\r\n\r\n"
                    + error.Message
                    + "\r\n\r\n程序位置：\r\n"
                    + target,
                "Multiagent Studio 无法启动",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
        }
    }
}
