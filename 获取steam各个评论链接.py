import time
from DrissionPage import ChromiumPage


page = ChromiumPage()

count=1


# 游戏的评测页面(以明末为例)
steam_url = 'https://steamcommunity.com/app/2277560/positivereviews/?p=1&browsefilter=mostrecent&filterLanguage=schinese'

page.set.window.size(1600,1000)

page.get(steam_url)

while True:
    page.scroll.to_bottom()

    # 1. 先判断“到底”提示
    no_more = page.ele('#NoMoreContent')
    if no_more and no_more.states.is_displayed and '没有更多内容了。太伤感了。' in no_more.text:
        print('到底了，结束')
        break

    # 2. 没到底就执行 Steam 的加载函数
    page.run_js('CheckForMoreContent();',timeout=300)
    time.sleep(0.2)   # 等后端返回并渲染

elements = page.eles('xpath://div[@class="apphub_CardRow"]')
# 每个评论页面
with open('评论URL.txt', 'w', encoding='utf-8') as f:
    for ele in elements:
        url = ele.ele('xpath://@data-modal-content-url')
        f.write(url + '\n')
        print(count,url)
        count+=1

