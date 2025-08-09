from datetime import datetime
import re
import time
from lxml import etree
import requests
import pymysql


# ----------------- 浏览器标识配置 -----------------
header = {
   "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
   'Accept-Language': 'zh-CN,zh;q=0.9',
   "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",
}

# ----------------- 数据库配置 -----------------
DB_CFG = dict(
    host="localhost",
    port=3306,
    user="root",
    password="123456",   # 改成你自己的
    db="steam",          # 你自己的库名
    charset="utf8mb4"
)

# 初始化数据库：建库建表
def init_db():
    conn = pymysql.connect(**DB_CFG)
    try:
        with conn.cursor() as cur:
            # 如果库不存在会自动创建（可选）
            cur.execute("CREATE DATABASE IF NOT EXISTS steam CHARACTER SET utf8mb4;")
            conn.select_db(DB_CFG["db"])

            create_sql = """
            CREATE TABLE IF NOT EXISTS steam_sql (
                用户名 VARCHAR(128),
                评论页面 VARCHAR(512) PRIMARY KEY,
                评价 VARCHAR(32),
                评论 TEXT,
                状态 VARCHAR(32) NULL,
                有价值数 INT NULL,
                欢乐数 INT NULL,
                发布时间 DATETIME NULL,
                修改时间 DATETIME NULL,
                评论人数 INT NULL,
                两周内时长 VARCHAR(32) NULL,
                总时长 VARCHAR(32) NULL,
                等级 INT NULL,
                徽章数 INT NULL,
                库存数 INT NULL,
                评测数 INT NULL,
                好友数 INT NULL,
                组数 INT NULL,
                游戏1 VARCHAR(128) NULL,
                时长1 VARCHAR(32) NULL,
                成就1 VARCHAR(32) NULL,
                游戏2 VARCHAR(128) NULL,
                时长2 VARCHAR(32) NULL,
                成就2 VARCHAR(32) NULL,
                游戏3 VARCHAR(128) NULL,
                时长3 VARCHAR(32) NULL,
                成就3 VARCHAR(32) NULL,
                抓取时间 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            cur.execute(create_sql)
        conn.commit()
    finally:
        conn.close()


# 写入或更新单条数据
def save_to_db(row):
    """
    row 是 get_info() 返回的整条 tuple
    """
    conn = pymysql.connect(**DB_CFG)
    try:
        with conn.cursor() as cur:
            sql = """
            INSERT INTO steam_sql (
                用户名,评论页面,评价,评论,状态,有价值数,欢乐数,
                发布时间,修改时间,评论人数,两周内时长,总时长,
                等级,徽章数,库存数,评测数,好友数,组数,
                游戏1,时长1,成就1,游戏2,时长2,成就2,游戏3,时长3,成就3
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
            )
            ON DUPLICATE KEY UPDATE
                用户名=VALUES(用户名),
                评价=VALUES(评价),
                评论=VALUES(评论),
                状态=VALUES(状态),
                有价值数=VALUES(有价值数),
                欢乐数=VALUES(欢乐数),
                发布时间=VALUES(发布时间),
                修改时间=VALUES(修改时间),
                评论人数=VALUES(评论人数),
                两周内时长=VALUES(两周内时长),
                总时长=VALUES(总时长),
                等级=VALUES(等级),
                徽章数=VALUES(徽章数),
                库存数=VALUES(库存数),
                评测数=VALUES(评测数),
                好友数=VALUES(好友数),
                组数=VALUES(组数),
                游戏1=VALUES(游戏1),
                时长1=VALUES(时长1),
                成就1=VALUES(成就1),
                游戏2=VALUES(游戏2),
                时长2=VALUES(时长2),
                成就2=VALUES(成就2),
                游戏3=VALUES(游戏3),
                时长3=VALUES(时长3),
                成就3=VALUES(成就3),
                抓取时间=CURRENT_TIMESTAMP
            """
            cur.execute(sql, row)
        conn.commit()
    finally:
        conn.close()


# 定义一个函数来读取文件中的 URL
def read_urls_from_file(file_path):
    urls = []  # 创建一个空列表来存储 URL
    with open(file_path, 'r', encoding='utf-8') as file:  # 打开文件
        for line in file:  # 遍历文件的每一行
            line = line.strip()  # 去掉行首尾的空白字符（包括换行符）
            if line:  # 如果行不为空
                urls.append(line)  # 将 URL 添加到列表中
    return urls  # 返回包含所有 URL 的列表

# 提取并格式化时间
def format_steam_time(raw):
    # 去掉前缀
    cleaned = raw.replace("发布于：", "").replace("更新于：", "")
    # 正则提取
    full_match = re.search(
        r'(?:(\d{4}) 年 )?(\d{1,2}) 月 (\d{1,2}) 日 (上午|下午) (\d{1,2}):(\d{2})',
        cleaned
    )
    
    if not full_match:
        return None
    
    year_str, month, day, period, hour, minute = full_match.groups()

    # 年份
    year = int(year_str) if year_str else datetime.now().year

    # 转换为24小时制
    hour = int(hour)
    if period == '下午' and hour != 12:
        hour += 12
    if period == '上午' and hour == 12:
        hour = 0
    # 构造 datetime 对象（年份用当前年份）
    dt = datetime(year, int(month), int(day), hour, int(minute))
    return dt.strftime("%Y-%m-%d %H:%M")


# 获取用户信息
def user_info(user_url,header):
    response = etree.HTML(requests.get(url=user_url,headers=header).content.decode('utf-8'))

    # 判断是否触发反爬机制
    try:
        test = response.xpath('//*[@id="mainContents"]/div/h1/text()')[0]
        while test == '抱歉！':
            print("当前页面被反爬，暂停10秒")
            time.sleep(10)
            response = etree.HTML(requests.get(url=user_url,headers=header).content.decode('utf-8'))
            test = response.xpath('//*[@id="mainContents"]/div/h1/text()')[0]
    except:
        pass

    # 等级
    try:
        level = response.xpath('//*[@class="friendPlayerLevelNum"]/text()')[0]
        level = int(level)
    except:
        level = None
    
    # 徽章数
    try:
        badges = response.xpath('//span[contains(text(),"徽章")]/following-sibling::span/text()')[0]
        badges = int(badges.replace(',', '')) if badges else 0
    except:
        badges = None

    # 库存数
    try:
        games = response.xpath('//span[contains(text(),"游戏")]/following-sibling::span/text()')[0]
        games = int(games.replace(',', '')) if games else 0
    except:
        games = None

    # 评测数
    try:
        reviews = response.xpath('//span[contains(text(),"评测")]/following-sibling::span/text()')[0]
        recommended = int(reviews.replace(',', '')) if reviews else 0
    except:
        recommended = None

    # 好友数
    try:
        friends = response.xpath('//span[contains(text(),"好友")]/following-sibling::span/text()')[0]
        friends = int(friends.replace(',', '')) if friends else 0
    except:
        friends = None

    # 组数
    try:
        groups = response.xpath('//span[contains(text(),"组")]/following-sibling::span/text()')[0]
        groups = int(groups.replace(',', '')) if groups else 0
    except:
        groups = None

    # 最近游玩
    games_list = response.xpath('//div[@class="recent_game_content"]')

    # 初始化列表
    game = [None] * 3
    play_time = [None] * 3
    chievement = [None] * 3
    for i in range(3):
        # 前三游戏名称
        try:
            game[i] = games_list[i].xpath('.//div[@class="game_name"]/a/text()')[0].strip()
        except:
            game[i] = None
        # 游玩时长
        try:
            play_time[i] = games_list[i].xpath('.//div[@class="game_info_details"]/text()')[0].strip().split(' ')[1].replace(",",'')
        except:
            play_time[i] = None
        # 成就
        try:
            chievement[i] = games_list[i].xpath('.//span[@class="ellipsis"]/text()')[0].strip().replace(" of ", "/")
        except:
            chievement[i] = None

    # 返回等级、徽章数、库存数、评测数、好友数、组数、最近游玩前三游戏信息
    return level,badges,games,recommended,friends,groups,game[0],play_time[0],chievement[0],game[1],play_time[1],chievement[1],game[2],play_time[2],chievement[2]



# 获取评测信息
def get_info(url,header):
    response = etree.HTML(requests.get(url=url,headers=header).content.decode('utf-8'))

    # 用户名
    user_name = response.xpath('//*[@id="responsive_page_template_content"]/div/div[1]/div/div/span[1]/a/text()')[0].strip()

    # 用户主页
    user_url = response.xpath('//*[@id="responsive_page_template_content"]/div/div[1]/div/div/span[1]/a/@href')[0].strip()

    # 评价
    valuation = response.xpath('//*[@id="ReviewTitle"]/div[1]/div[1]/text()')[0].strip()

    # 评论
    recommend = ' '.join(' '.join(response.xpath('//*[@id="ReviewText"]//text()')).split()).replace('\u200b','')

    # 状态
    try:
        status = response.xpath('//*[@class="refunded tooltip"]//text()')[0].strip()[2:]
    except:
        status = "未退款"

    # 认为有价值人数
    try:
        help_text = response.xpath('//*[@id="leftContents"]/div[2]/text()[1]')[0]
        help = int(re.sub(r'[^\d]', '', help_text)) if help_text else 0
    except:
        help = 0

    # 认为欢乐人数
    try:
        happy_text = response.xpath('//*[@id="leftContents"]/div[2]/text()[2]')[0]
        happy = int(re.sub(r'[^\d]', '', happy_text)) if happy_text else 0
    except:
        happy = 0

    # 发布时间
    posted_time = format_steam_time(response.xpath('//*[@id="ReviewTitle"]/div[2]/text()[1]')[0].strip())

    # 修改时间
    try:
        updated_time = format_steam_time(response.xpath('//*[@id="ReviewTitle"]/div[2]/text()[2]')[0].strip())
    except:
        updated_time = None

    # 评论人数
    try:
        relpy_counts = response.xpath('//div[@class="commentthread_header_and_count"]//span[contains(@id,"totalcount")]/text()')[0]
        relpy_counts = int(re.sub(r'[^\d]', '', relpy_counts)) if relpy_counts else 0
    except:
        relpy_counts = 0

    # 游戏时间
    the_time = response.xpath('//*[@id="ReviewTitle"]/div[1]/div[2]/text()')[0].strip().split('/')

    # 两周内该游戏时长
    two_weeks_play_time = the_time[0].strip().split('周')[1].split('小时')[0].strip() if len(the_time) > 0 else None

    # 该游戏总共游玩时长
    all_time = the_time[1].strip().split(' ')[1] if len(the_time) > 1 else None


    return user_name,url,valuation,recommend,status,help,happy,posted_time,updated_time,relpy_counts,two_weeks_play_time,all_time,*user_info(user_url,header)

# 存入数据库
def load_to_sql(urls):
    # 构建容错列表
    defeat_url = []
    # 逐条抓取并入库
    for url in urls:
        try:
            row = get_info(url, header)
            save_to_db(row)
            print(f"[√] 已写入/更新：{url}")
        except Exception as e:
            print(f"[×] 处理失败：{url}，错误：{e}")
            print("等待10秒......")
            defeat_url.append(url)
            time.sleep(10)
    return defeat_url


# ----------------- 主程序 -----------------
if __name__ == '__main__':
    # 初始化数据库
    init_db()

    # 读取 URL 列表
    urls = read_urls_from_file('评论URL.txt.txt')

    # 构建容错列表
    defeat_url = load_to_sql(urls)
    while len(defeat_url) != 0:
        defeat_url = load_to_sql(defeat_url)

    

    print("爬取失败的URL:",defeat_url)