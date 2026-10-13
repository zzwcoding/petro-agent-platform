#!/usr/bin/env python3
"""手册 md → 网页（jiangjie.html）。"""
import os
import pathlib
import markdown

SITE = pathlib.Path(os.environ.get("SITE_DIR", "/tmp/onto-deploy/site"))
md_text = (SITE / "xiangmu.md").read_text(encoding="utf-8")
body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>本体方法论·概念与应用要点手册</title>
<style>
  body{margin:0;background:#eee8d5;font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif;}
  .top{position:sticky;top:0;background:#fdf6e3;border-bottom:1px solid #cec7a8;padding:10px 20px;z-index:9;}
  .top a{color:#268bd2;text-decoration:none;font-size:14px;}
  .wrap{max-width:880px;margin:0 auto;background:#fdf6e3;min-height:100vh;padding:36px 44px 90px;
    color:#586e75;font-size:14.5px;line-height:1.85;}
  h1{font-size:24px;color:#073642;border-bottom:3px solid #268bd2;padding-bottom:10px;}
  h2{font-size:19px;color:#073642;margin-top:38px;border-left:5px solid #268bd2;padding-left:10px;}
  h3{font-size:16px;color:#586e75;margin-top:28px;}
  blockquote{margin:12px 0;padding:8px 16px;background:#eee8d5;border-left:4px solid #b58900;color:#657b83;}
  table{border-collapse:collapse;width:100%;margin:12px 0;}
  th,td{border:1px solid #cec7a8;padding:6px 10px;font-size:13px;text-align:left;}
  th{background:#eee8d5;}
  code{font-family:Menlo,Consolas,monospace;font-size:12.5px;background:#eee8d5;padding:1px 5px;border-radius:4px;}
  pre code{display:block;padding:12px;overflow-x:auto;line-height:1.6;}
  hr{border:none;border-top:1px solid #cec7a8;margin:30px 0;}
  li{margin:5px 0;}
</style>
</head>
<body>
<div class="top"><a href="../index.html">← 返回目录</a></div>
<div class="wrap">
BODY_PLACEHOLDER
</div>
</body>
</html>
"""
html = html.replace("BODY_PLACEHOLDER", body)
(SITE / "jiangjie.html").write_text(html, encoding="utf-8")
print("jiangjie.html", len(html), "chars")
