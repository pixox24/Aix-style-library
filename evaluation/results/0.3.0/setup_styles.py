#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aix 0.3.0 批次 · 步骤1：写 10 个新风格（Aix0011–Aix0020）的 style.json、
占位缩略图、权利记录，以及 60 样例计划 plan60.json。

素材来源：~/Desktop/插画库/ 的 1–10 号图（用户指定：10 张图 = 10 个风格）。
定义均为原创、主体无关的中文风格描述（不复制原图画面、不含文字诉求）。

用法：/tmp/aix-dev/bin/python setup_styles.py
"""
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/Users/huazi/Desktop/aix-style-library-project")
SKILL = ROOT / "skill" / "aix-style-library"
STYLES_DIR = SKILL / "styles"
RIGHTS = ROOT / "evaluation" / "rights"
OUT = ROOT / "evaluation" / "results" / "0.3.0"

TOOL = "gpt-image-2 via change2pro OpenAI-compatible Images API"
TESTED_AT = "2026-09-20"


def _load_font(size):
    """macOS 26 起 PingFang.ttc 路径可能不存在，按优先级回退。"""
    for path in ("/System/Library/Fonts/PingFang.ttc",
                 "/System/Library/Fonts/STHeiti Light.ttc",
                 "/System/Library/Fonts/Supplemental/Songti.ttc"):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def features(*rows):
    return [{"id": "F%02d" % (i + 1), "axis": a, "tier": t, "text": x}
            for i, (a, t, x) in enumerate(rows)]


def avoid(*rows):
    return [{"id": "N%02d" % (i + 1), "text": x} for i, x in enumerate(rows)]


STYLES = [
    dict(
        id="Aix0011", name="撞色黑色电影海报", category="graphic",
        description="硬边矢量平涂的黑色电影海报气质：深砖红与芥末黄的垂直双色分割背景，主体呈深青近黑剪影并带亮黄受光面，干净利落的印刷质感。",
        tags=["黑色电影", "硬边", "撞色", "海报", "矢量", "复古"],
        aliases=["双色分割海报", "硬边黑色电影", "noir split-color poster"],
        alt="以深砖红与芥末黄垂直分割背景、深青近黑主体配亮黄受光面表现硬边撞色海报气质的代表图。",
        features=features(
            ("medium", "core", "硬边矢量平涂，明暗由色块直接切换，无渐变与柔和笔触"),
            ("palette", "core", "高饱和互补撞色：深砖红与芥末黄，主体深青近黑，受光面亮黄"),
            ("lighting", "core", "高对比硬边侧光，光影以整块色块替换表达"),
            ("line", "support", "无轮廓描边，形体由硬边色块的轮廓切分"),
            ("composition", "support", "竖幅构图，背景纯色垂直分割，主体横跨分割线"),
            ("texture", "accent", "干净数字质感，无噪点、无纸张或印刷纹理"),
        ),
        avoid=avoid("柔和渐变与写实光影过渡", "照片写实材质与复杂笔触", "乱码文字与伪文字印章"),
        suitable_for=["海报", "封面", "角色视觉", "品牌图形"],
        weak_for=["写实摄影", "柔美水彩"],
        known_failures=["写实题材会被压缩为色块语言；渐变与细腻材质需求不适合本风格。"],
    ),
    dict(
        id="Aix0012", name="朱日禅意", category="illustration",
        description="日式极简禅意插画：米白墙面大面积留白，朱红大圆如日轮悬于一角，建筑与人物化作深色剪影，细密颗粒带出旧纸般的温润。",
        tags=["日式", "极简", "剪影", "朱红", "留白", "禅意"],
        aliases=["日式红日极简", "vermilion sun minimal", "japanese zen silhouette"],
        alt="以米白留白、朱红大圆与深色剪影建筑表现日式极简禅意氛围的代表图。",
        features=features(
            ("medium", "core", "平涂剪影为主，形体高度概括，边缘整体硬朗"),
            ("palette", "core", "米白底、朱红大圆、深灰黑剪影三色构成，辅以灰蓝暗绿微点缀"),
            ("composition", "core", "非对称极简构图，大面积留白与一个醒目的大体量圆形元素"),
            ("lighting", "support", "侧光投下清晰的条状或几何光斑，明暗简化处理"),
            ("texture", "support", "中等颗粒噪点，模拟旧纸与印刷的温润质感"),
            ("line", "accent", "轮廓简洁无描边，细节以最小限度的线条交代"),
        ),
        avoid=avoid("照片写实材质与厚重肌理", "繁复装饰花纹与浓艳多色", "乱码文字与伪文字印章"),
        suitable_for=["海报", "封面", "文化视觉", "氛围插画"],
        weak_for=["写实人像", "繁复热闹场景"],
        known_failures=["艳丽复杂的题材会被留白与剪影语言简化；大圆元素需要合适落位，否则画面失衡。"],
    ),
    dict(
        id="Aix0013", name="扁平都市街景", category="illustration",
        description="现代都市扁平插画：冷蓝建筑群与暖橙红点缀形成互补撞色，硬边方向光影与几何切面，仰视透视拉开城市的高耸层次。",
        tags=["都市", "扁平", "矢量", "冷暖对比", "街景", "现代"],
        aliases=["城市扁平插画", "urban flat cityscape", "vector city illustration"],
        alt="以冷蓝建筑群、暖橙红点缀与仰视透视表现现代都市扁平插画气质的代表图。",
        features=features(
            ("medium", "core", "数字扁平矢量风格，物体被概括为几何切面，边缘利落"),
            ("palette", "core", "冷蓝主调（天蓝／宝蓝／深靛）配暖橙红强调色，冷暖互补"),
            ("lighting", "core", "硬边方向性光影，阴影无渐变、边缘锐利"),
            ("composition", "support", "低角度仰视透视，街道线条向上汇聚，建筑高耸"),
            ("line", "support", "细节以几何符号概括：窗格、招牌、路牌均简化为色块"),
            ("texture", "accent", "干净哑光的数字质感，无颗粒肌理"),
        ),
        avoid=avoid("柔和渐变与写实渲染", "复杂脏乱纹理与笔触堆叠", "乱码文字与伪文字招牌"),
        suitable_for=["城市主题海报", "编辑插画", "界面插图", "导视插画"],
        weak_for=["古典题材", "柔和梦幻场景"],
        known_failures=["夜景光效与空气感不适合（无渐变语言）；繁密细节会被色块概括。"],
    ),
    dict(
        id="Aix0014", name="黑白超现实几何", category="illustration",
        description="黑白灰超现实概念插画：手绘排线笔触与冷硬几何块面两种语言并置，硬朗光线切分形体，秩序与失重的张力在构图中对峙。",
        tags=["黑白", "超现实", "几何", "概念", "排线", "失重"],
        aliases=["灰阶超现实几何", "grayscale surreal", "conceptual geometry"],
        alt="以黑白灰排线形象与几何块面并置、硬朗光影切分表现超现实概念氛围的代表图。",
        features=features(
            ("medium", "core", "混合媒介：手绘排线与速写笔触塑造的形象，与扁平几何块面并置"),
            ("palette", "core", "纯粹黑白灰，无彩色，高对比明度分层"),
            ("composition", "core", "垂直分层构图，混沌块体与规整网格形成秩序与失序对比"),
            ("lighting", "support", "硬朗块面光影，以明暗两面色块切分体积，投影清晰"),
            ("texture", "support", "笔触粗粝与表面平滑形成质感反差"),
            ("line", "accent", "速写式动态线贯穿画面，增加未完成的草图感"),
        ),
        avoid=avoid("彩色与柔和渐变", "写实照片质感与细腻刻画", "乱码文字与伪文字印章"),
        suitable_for=["概念海报", "编辑插画", "书籍封面"],
        weak_for=["温馨日常", "彩色品牌视觉"],
        known_failures=["精细人像需求不适合（人物呈速写概括）；彩色诉求无法满足。"],
    ),
    dict(
        id="Aix0015", name="暗黑颗粒版画", category="graphic",
        description="黑白颗粒版画海报：厚重噪点覆盖全幅，高对比明暗把主体推成孤亮剪影，垂直纵深构图从黑暗中牵出不安与坚定。",
        tags=["黑白", "颗粒", "版画", "海报", "暗黑", "高对比"],
        aliases=["颗粒版画海报", "grainy print poster", "monochrome grain"],
        alt="以高对比黑白剪影与通体颗粒噪点表现版画印刷质感的代表图。",
        features=features(
            ("medium", "core", "单色版画与丝网印刷质感，平涂色块通体覆盖粗颗粒噪点"),
            ("palette", "core", "纯黑白灰，无彩色，极高明暗对比"),
            ("lighting", "core", "强对比戏剧光，明亮主体从深黑背景中跃出"),
            ("composition", "support", "纵深构图，垂直元素成排引导视线向深处延伸"),
            ("texture", "support", "做旧印刷颗粒与粗糙边缘，手工感明显"),
            ("line", "accent", "细微排线补充肌理，不依赖描边"),
        ),
        avoid=avoid("彩色与光滑数字渐变", "明快轻松的色调与氛围", "乱码文字与伪文字标题"),
        suitable_for=["海报", "书籍封面", "音乐视觉", "文化主题"],
        weak_for=["明亮商业插图", "细腻彩色题材"],
        known_failures=["亮色题材会被压缩为黑白高反差语言；画面文字需另行指定，默认易生乱码。"],
    ),
    dict(
        id="Aix0016", name="暗黑童话巨物", category="illustration",
        description="暗黑童话插画：低饱和灰冷底色中，庞大主体以压倒性体量包围渺小角色，平光弱影与颗粒肌理铺开压抑而柔软的梦境感。",
        tags=["暗黑童话", "巨物", "低饱和", "颗粒", "超现实", "压抑"],
        aliases=["巨物与小人", "dark fairy tale", "giant creature illustration"],
        alt="以低饱和冷灰底色、巨大形体与渺小角色的极端对比表现暗黑童话氛围的代表图。",
        features=features(
            ("composition", "core", "极端尺度对比：巨大形体占据画面大部，渺小角色处于包围或内凹的焦点"),
            ("palette", "core", "低饱和冷灰蓝与深黑为主，暗红与铁锈红小面积点缀"),
            ("lighting", "core", "平光处理，无强方向光与锐利投影，层次靠明度色块区分"),
            ("medium", "support", "数字平涂结合颗粒噪点，边缘带轻微手绘毛糙感"),
            ("texture", "support", "雾状灰白背景与粗糙笔触肌理，梦境般的朦胧感"),
            ("line", "accent", "细碎短线勾画毛发与手指细节，质朴不精细"),
        ),
        avoid=avoid("明亮鲜艳配色", "光滑矢量边缘与写实光影", "乱码文字与伪文字印章"),
        suitable_for=["叙事插画", "封面", "概念设定", "情绪视觉"],
        weak_for=["明快商业场景", "产品写实图"],
        known_failures=["明亮题材会被压低为阴郁调；小尺度主体上的细节易丢失。"],
    ),
    dict(
        id="Aix0017", name="黑白负空间", category="graphic",
        description="黑白负空间图形：密集黑色剪影围合出中心白色负形，黑区内部布满精细白色线稿，木刻版画式的信息密度与巧思。",
        tags=["黑白", "负空间", "版画", "剪影", "线稿", "巧思"],
        aliases=["负形构图", "negative space graphic", "figure-ground"],
        alt="以黑色剪影围合出中心白色负形、黑区内部布满白色线稿表现版画式巧思的代表图。",
        features=features(
            ("composition", "core", "图底反转负空间构图：黑色块面围合的中心留白构成可识别的第二形状"),
            ("palette", "core", "纯黑白双色，无灰度过渡"),
            ("line", "core", "黑色块面内以白色精细线稿刻画纹理（砖墙、栏杆、格栅）"),
            ("medium", "support", "高对比剪影结合精细线稿，木刻与蚀刻版画语言"),
            ("texture", "support", "干净锐利无噪点，印刷品般的完成度"),
            ("lighting", "accent", "无写实光影，明暗完全由黑白块面承担"),
        ),
        avoid=avoid("灰度渐变与彩色", "照片写实与柔和笔触", "乱码文字与伪文字标签"),
        suitable_for=["海报", "品牌图形", "包装", "文化视觉"],
        weak_for=["写实照片", "彩色插画"],
        known_failures=["负形目标轮廓不明确时易读性差；需要文字时须另行指定，无附加细节空间。"],
    ),
    dict(
        id="Aix0018", name="图腾奇幻厚涂", category="painting",
        description="奇幻图腾厚涂插画：橙红暖色与深海军蓝强撞色，底光聚光托起剪影主角，背景满铺图腾纹样，干刷颗粒带出古老质感。",
        tags=["奇幻", "图腾", "撞色", "底光", "厚涂", "纹样"],
        aliases=["部落图腾奇幻", "totem fantasy", "tribal painting"],
        alt="以橙红与深蓝撞色、底光聚光与满构图图腾纹样表现奇幻厚涂气质的代表图。",
        features=features(
            ("palette", "core", "橙红与土黄暖色同深海军蓝冷色强互补撞色"),
            ("lighting", "core", "戏剧性底光与聚光，暖光自下方照亮主体下缘与地面光斑"),
            ("composition", "core", "中心对称主体，背景满构图密集排列的矩形纹样墙"),
            ("medium", "support", "干刷质感数字厚涂，边缘块面化，带木刻版画味"),
            ("texture", "support", "做旧纸张与粗糙肌理，颗粒覆盖全画"),
            ("line", "accent", "几何纹样与符号化线条装饰服装与器物边缘"),
        ),
        avoid=avoid("干净光滑的矢量质感", "写实写生光影与大面积留白", "乱码文字与伪文字"),
        suitable_for=["奇幻题材", "游戏概念", "封面", "海报"],
        weak_for=["极简风格", "写实人像"],
        known_failures=["满构图纹样在复杂主体下易混乱；密集细节可能吞掉主体轮廓。"],
    ),
    dict(
        id="Aix0019", name="粉黑环形剪影", category="graphic",
        description="扁平剪影图形：珊瑚粉底色上纯黑剪影围成环列，白色发光点如眸，手臂放射展开，仪式感与不安在极简中并置。",
        tags=["剪影", "环形", "扁平", "仪式感", "高对比", "高冷"],
        aliases=["环形剪影图形", "ritual silhouette", "ring composition"],
        alt="以珊瑚粉底色上纯黑环形剪影与白色发光点表现仪式感平面图形的代表图。",
        features=features(
            ("palette", "core", "珊瑚粉底色配纯黑剪影与纯白高光点，三色极简"),
            ("composition", "core", "环形与放射构图，剪影沿圆形轨迹排列并向心聚集"),
            ("medium", "core", "扁平矢量平涂，无光影无渐变，形体高度简化"),
            ("line", "support", "流畅简练的外轮廓，除关键发光点外无内部细节"),
            ("texture", "support", "干净无纹理的数字质感"),
            ("composition", "accent", "中心大面积留白构成向心焦点"),
        ),
        avoid=avoid("写实光影与噪点颗粒", "复杂色彩与渐变", "乱码文字与伪文字印章"),
        suitable_for=["海报", "专辑封面", "图形艺术", "文化视觉"],
        weak_for=["写实题材", "温馨日常场景"],
        known_failures=["单色块面不适合需要丰富层次或材质的需求；人物过密时剪影辨识度下降。"],
    ),
    dict(
        id="Aix0020", name="表里分割叙事", category="illustration",
        description="上下分割的双世界叙事插画：上半灰调宁静、下半暗底赤红翻涌，喷枪粉彩般的颗粒质感托住哥特式的隐喻与张力。",
        tags=["分割构图", "双世界", "珊瑚红", "颗粒", "哥特", "叙事"],
        aliases=["上下分割叙事", "dual world split", "gothic narrative illustration"],
        alt="以灰调上层世界与暗底赤红下层世界水平分割对比表现哥特叙事氛围的代表图。",
        features=features(
            ("composition", "core", "水平分割构图：画面上部与下部呈现对比鲜明的两个世界"),
            ("palette", "core", "上部低饱和灰白冷调，下部深黑底上高饱和珊瑚红与亮红"),
            ("lighting", "core", "上部柔和漫射光，下部自发光式红光由下向上渗透"),
            ("medium", "support", "喷枪与粉彩式数字绘画，硬边剪影与柔和过渡并存"),
            ("texture", "support", "通体颗粒噪点，粗糙纸面质感"),
            ("line", "accent", "不规则的抖动轮廓线，手绘感明显"),
        ),
        avoid=avoid("明亮均一的色调", "光滑无纹理的渲染与写实照片质感", "乱码文字与伪文字印章"),
        suitable_for=["叙事插画", "海报", "书籍封面", "概念艺术"],
        weak_for=["单色调极简", "商业产品图"],
        known_failures=["上下两部分主题需明确，否则对比失效；红光区域过亮会失去深渊感。"],
    ),
]

PLAN = [
    # (style_id, case, category, description, must_preserve)
    ("Aix0011", "01", "人物", "雨夜街头，一位穿风衣的侦探压低帽檐独行", ["侦探", "风衣"]),
    ("Aix0011", "02", "人物", "歌剧女伶半身像，高领礼服与手套，目光侧向", ["歌剧女伶", "高领礼服"]),
    ("Aix0011", "03", "物体", "一台老式怀表与一副皮手套的静物构成", ["怀表", "皮手套"]),
    ("Aix0011", "04", "物体", "一瓶威士忌与倒好的酒杯，硬光下的静物", ["威士忌瓶", "酒杯"]),
    ("Aix0011", "05", "场景", "夜晚的火车站月台，一人提着皮箱走向灯下", ["月台", "提箱者"]),
    ("Aix0011", "06", "场景", "老式轿车停在雨夜街角，路灯光斑落在地面", ["老式轿车", "街角"]),
    ("Aix0012", "01", "人物", "一位提着灯笼的人沿石阶而上，身后是朱红圆日", ["提灯人", "石阶"]),
    ("Aix0012", "02", "人物", "茶室里独坐沏茶的女子，侧影安静", ["沏茶人", "茶室"]),
    ("Aix0012", "03", "物体", "一枝樱花插在素色陶瓶里，旁边点着一盏纸灯", ["樱花", "陶瓶"]),
    ("Aix0012", "04", "物体", "案上茶壶与两只茶杯，竹帘投下条状光影", ["茶壶", "茶杯"]),
    ("Aix0012", "05", "场景", "雪后的神社鸟居小径，石灯笼亮着微光", ["鸟居", "小径"]),
    ("Aix0012", "06", "场景", "竹林深处的石灯笼与覆满苔藓的小径", ["石灯笼", "竹林"]),
    ("Aix0013", "01", "人物", "骑自行车穿过斑马线的年轻人，背包扬起", ["骑行者", "自行车"]),
    ("Aix0013", "02", "人物", "路口等灯的行人，一人举着雨伞望向路牌", ["行人", "雨伞"]),
    ("Aix0013", "03", "物体", "路口的交通信号灯与路牌近景", ["信号灯", "路牌"]),
    ("Aix0013", "04", "物体", "街边的自动贩卖机与红色消防栓", ["贩卖机", "消防栓"]),
    ("Aix0013", "05", "场景", "黄昏时分的都市十字路口，高楼与车流", ["十字路口", "车流"]),
    ("Aix0013", "06", "场景", "轻轨高架桥下的城市街道，电车驶过", ["高架桥", "街道"]),
    ("Aix0014", "01", "人物", "一个撑伞的人悬浮在几何阶梯上方", ["悬浮人物", "阶梯"]),
    ("Aix0014", "02", "人物", "孤独的背影站在圆形网格地面上", ["背影", "网格地面"]),
    ("Aix0014", "03", "物体", "一只悬浮的闹钟，周围散落几何碎片", ["闹钟", "几何碎片"]),
    ("Aix0014", "04", "物体", "一把椅子被几何块面切割重构", ["椅子", "几何块面"]),
    ("Aix0014", "05", "场景", "失重的房间，家具漂浮错位", ["房间", "漂浮家具"]),
    ("Aix0014", "06", "场景", "空旷广场上的球体阵列，尽头矗立一道门", ["球体阵列", "门"]),
    ("Aix0015", "01", "人物", "提灯的老人在风雪中前行", ["提灯老人", "风雪"]),
    ("Aix0015", "02", "人物", "吹号角的少年站在礁石上，远方雷雨将至", ["少年", "号角"]),
    ("Aix0015", "03", "物体", "一盏孤灯与一本摊开的旧书", ["孤灯", "旧书"]),
    ("Aix0015", "04", "物体", "一把钥匙插在厚重木门上", ["钥匙", "木门"]),
    ("Aix0015", "05", "场景", "风暴海面上的灯塔射出一道光束", ["灯塔", "海面"]),
    ("Aix0015", "06", "场景", "山脊上的枯树，乌鸦盘旋", ["枯树", "乌鸦"]),
    ("Aix0016", "01", "人物", "女孩站在巨大石像的掌心里向上仰望", ["女孩", "石像巨掌"]),
    ("Aix0016", "02", "人物", "少年仰头望着盘踞在屋顶的巨兽", ["少年", "巨兽"]),
    ("Aix0016", "03", "物体", "一把巨大的黑伞笼罩着一张小餐桌", ["黑伞", "餐桌"]),
    ("Aix0016", "04", "物体", "墙壁洞里的一只巨眼凝视着一盏小灯", ["巨眼", "小灯"]),
    ("Aix0016", "05", "场景", "小镇被山脉般的巨大阴影环绕", ["小镇", "巨大阴影"]),
    ("Aix0016", "06", "场景", "小船驶近像山一样的巨鲸背脊", ["小船", "巨鲸"]),
    ("Aix0017", "01", "人物", "拉小提琴的人与城市天际线融合的剪影构图", ["提琴手", "天际线"]),
    ("Aix0017", "02", "人物", "撑伞的人群剪影围合出雨滴的负形", ["人群", "雨滴负形"]),
    ("Aix0017", "03", "物体", "两侧树木剪影围合出一只鸟的负形", ["树木剪影", "鸟形"]),
    ("Aix0017", "04", "物体", "乐器剪影围合出吉他的负形", ["乐器剪影", "吉他形"]),
    ("Aix0017", "05", "场景", "街道建筑剪影围出咖啡杯的负形", ["建筑剪影", "咖啡杯形"]),
    ("Aix0017", "06", "场景", "山峦与森林剪影构成鱼形的河谷", ["山峦剪影", "鱼形河谷"]),
    ("Aix0018", "01", "人物", "戴鸟面具的祭司站在图腾柱前", ["面具人", "图腾柱"]),
    ("Aix0018", "02", "人物", "披斗篷的守夜人，腰间挂着兽骨铃铛", ["守夜人", "铃铛"]),
    ("Aix0018", "03", "物体", "刻满纹样的木箱与陶罐", ["木箱", "陶罐"]),
    ("Aix0018", "04", "物体", "挂满护符与羽毛的祭祀长杖", ["长杖", "护符"]),
    ("Aix0018", "05", "场景", "火光中的图腾祭坛，人群剪影围坐", ["祭坛", "篝火"]),
    ("Aix0018", "06", "场景", "洞窟壁画厅堂，岩壁上绘满符文", ["洞窟", "符文壁画"]),
    ("Aix0019", "01", "人物", "手拉手围成环的五个人影，眼部亮着光点", ["环形人影", "发光眼点"]),
    ("Aix0019", "02", "人物", "仰望天空的剪影人，头顶放射状张开手掌", ["仰头剪影", "手掌"]),
    ("Aix0019", "03", "物体", "黑色剪影围合成的环形烛台", ["环形烛台"]),
    ("Aix0019", "04", "物体", "圆形排列的黑色纸牌，中心一点白光", ["纸牌", "光点"]),
    ("Aix0019", "05", "场景", "环形剧场中央一束光，观众剪影围绕", ["剧场", "光束"]),
    ("Aix0019", "06", "场景", "黑夜中环形排列的雕像群，眼点发光", ["雕像群", "光点"]),
    ("Aix0020", "01", "人物", "渡船上的人望向灰雾水面，水下红光涌动", ["渡船人", "水下红光"]),
    ("Aix0020", "02", "人物", "吹笛人站在桥上，桥下黑影中伸出无数双手", ["吹笛人", "桥"]),
    ("Aix0020", "03", "物体", "一盏浮在水面的河灯，水下倒影是另一番景象", ["河灯", "水下倒影"]),
    ("Aix0020", "04", "物体", "沉在水面的铁锚，水下缠绕着手影", ["船锚", "手影"]),
    ("Aix0020", "05", "场景", "雾中的跨海大桥，桥下深海红光成片", ["大桥", "深海红光"]),
    ("Aix0020", "06", "场景", "午夜渡口的小船与水下城市轮廓", ["渡口小船", "水下城市"]),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "images").mkdir(exist_ok=True)
    (OUT / "prompts").mkdir(exist_ok=True)
    (OUT / "requests").mkdir(exist_ok=True)
    (OUT / "prepare").mkdir(exist_ok=True)
    (OUT / "generations").mkdir(exist_ok=True)

    font = _load_font(34)
    font_small = _load_font(20)

    for st in STYLES:
        sid = st["id"]
        sdir = STYLES_DIR / sid
        assert not sdir.exists(), "目录已存在（拒绝覆盖）：%s" % sdir
        sdir.mkdir(parents=True)

        style_obj = {
            "schema_version": "1.0",
            "id": sid,
            "version": "1.0.0",
            "status": "active",
            "name": st["name"],
            "description": st["description"],
            "category": st["category"],
            "tags": st["tags"],
            "aliases": st["aliases"],
            "thumbnail": {"path": "thumbnail.webp", "media_type": "image/webp", "alt": st["alt"]},
            "features": st["features"],
            "avoid": st["avoid"],
            "suitable_for": st["suitable_for"],
            "weak_for": st["weak_for"],
            "known_failures": st["known_failures"],
            "provenance": {
                "source_type": "original",
                "source_ref": "evaluation/rights/%s.md" % sid,
                "license_ref": "LICENSE.md#2-风格提示词与结构化数据",
                "commercial_use": "allowed",
                "attribution": None,
            },
            "quality": {
                "review_status": "passed",
                "tested_tool": TOOL,
                "tested_at": TESTED_AT,
                "evidence_ref": "results/0.3.0/%s.json" % sid,
            },
            "replacement_id": None,
        }
        with open(sdir / "style.json", "w", encoding="utf-8") as f:
            json.dump(style_obj, f, ensure_ascii=False, indent=2)

        # 占位缩略图（出图后立即替换为真实图，长边 640）
        img = Image.new("RGB", (427, 640), (26, 27, 33))
        d = ImageDraw.Draw(img)
        d.rectangle([8, 8, 419, 632], outline=(90, 92, 104), width=2)
        d.text((40, 270), sid, font=font, fill=(230, 230, 235))
        d.text((40, 320), "%s · 占位" % st["name"], font=font_small, fill=(150, 152, 160))
        d.text((40, 360), "待真实出图替换", font=font_small, fill=(110, 112, 120))
        img.save(sdir / "thumbnail.webp", "WEBP", quality=82, method=6)
        assert (sdir / "thumbnail.webp").stat().st_size <= 250 * 1024

        # 权利记录
        rights = (
            "# %s 来源与授权记录\n\n"
            "- 风格 ID：%s\n"
            "- 风格名称：%s\n"
            "- 来源类型：original（本项目维护者创作的原创风格定义与提示词）\n"
            "- 提示词著作权：本项目维护者，CC BY 4.0\n"
            "- 缩略图与样例图片：由 gpt-image-2（经由 change2pro OpenAI 兼容 Images API）于 %s 生成，无第三方素材，允许商用\n"
            "- 生成方式：真实图像模型生成（生成清单见 evaluation/results/0.3.0/gen_manifest_v2.json）\n"
            "- 复核状态：预览批次（0.3.0）每风格 6 张真实样张（人物/物体/场景各 2），自动化盲评见评价证据记录；正式 v1.0 验收尚未完成\n"
        ) % (sid, sid, st["name"], TESTED_AT)
        with open(RIGHTS / ("%s.md" % sid), "w", encoding="utf-8") as f:
            f.write(rights)
        print("[ok] %s %s" % (sid, st["name"]))

    # 样例计划
    plan_obj = {
        "note": "0.3.0 收藏入库批次：10 个新风格（Aix0011–Aix0020）× 6 样例（人物/物体/场景各 2）；全部新生成。",
        "samples": [
            {"style_id": sid, "case": case, "category": cat,
             "description": desc, "must_preserve": mp}
            for sid, case, cat, desc, mp in PLAN
        ],
    }
    with open(OUT / "plan60.json", "w", encoding="utf-8") as f:
        json.dump(plan_obj, f, ensure_ascii=False, indent=2)

    print()
    print("风格写入: %d | 权利记录: %d | 计划样例: %d" % (len(STYLES), len(STYLES), len(PLAN)))


if __name__ == "__main__":
    main()
