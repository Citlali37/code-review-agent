# 作业提交步骤

## 1. 最终检查

在项目目录运行测试：

```powershell
py -3 -m unittest discover -s tests -v
```

确认输出中的所有测试都是 `ok`，最后显示 `OK`。

检查并推送 GitHub：

```powershell
git status
git push
```

`git status` 应显示本地分支已经与 `origin/main` 同步，且没有待提交修改。

## 2. 创建安全压缩包

不要直接在资源管理器中压缩整个项目，因为那样可能把 `.env` 和 API Key 一起打包。

在项目目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_submission.ps1
```

脚本会根据 Git 已提交的文件创建 `2412190733干宸骅.zip`，因此不会包含 `.env`、`.git`、缓存文件或其他未追踪内容。如果存在尚未提交的改动，脚本会停止并提醒先提交。

## 3. 提交内容

按照作业说明提交：

- GitHub 仓库链接：`https://github.com/Citlali37/code-review-agent`
- 备份压缩包：`2412190733干宸骅.zip`，必须小于 200 MB
- 一分钟以内演示视频：可选

在课程提交平台找到 `001Homework1`，上传压缩包，并按平台要求填写 GitHub 链接。演示视频不是必交内容；如果选择提交，应录制当前版本并控制在一分钟以内。

## 4. 提交后复查

- 在未登录 GitHub 的浏览器窗口中打开仓库，确认老师可以访问；私有仓库则需要邀请老师或助教。
- 下载自己刚上传的压缩包，确认可以解压并包含 README、设计文档、源代码和测试。
- 再次确认压缩包内没有 `.env`，也没有任何 API Key。
