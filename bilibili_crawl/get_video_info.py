import re
import json
import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class BilibiliVideoInfoFetcher:
    def __init__(self, chromedriver_path):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 隐藏浏览器窗口
        chrome_options.add_argument("--disable-gpu")  # 禁用GPU加速
        self.driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options)
        self.video_dict = {}  # 在此处初始化 video_dict
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': '',
            'Origin': 'https://www.bilibili.com',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'DNT': '1',
        }
    def choose_type(self, str):
        if str == "最多弹幕":
            order = "dm"
        elif str == "最多播放":
            order = "clcik"
        elif str == "最新发布":
            order = "pubdate"
        elif str == "最多收藏":
            order = "stow"
        elif str == "综合排行":
            order = "无"
        return order

    def search_video_selenium(self, search_name, pages, search_type):
        # 使用Selenium搜索视频，并返回视频信息字典
        print(f"开始搜索关键词：{search_name}，共{pages}页")

        for page in range(1, pages + 1):
            print(f"正在搜索第{page}页...")
            order = self.choose_type(search_type)
            if order == "无":
                # if page == 1:
                #     url = f'https://search.bilibili.com/video?keyword={search_name}&single_column=0&'
                # else:
                url = f'https://search.bilibili.com/video?keyword={search_name}&single_column=0&&page={page}'
            else:
                url = f'https://search.bilibili.com/video?keyword={search_name}&single_column=0&&order={order}&page={page}'

            self.driver.get(url)
            print(f"正在搜索网页 {url}")

            try:
                # 等待页面加载视频链接
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/video/BV"]'))
                )
            except TimeoutException:
                print("页面加载超时，未找到视频链接")
                continue

            try:
                # 查找不包含 "hide" 类的所有视频项
                visible_videos = self.driver.find_elements(By.XPATH,
                                                           "//div[contains(@class, 'video-list-item') and not(contains(@class, 'hide'))]")

                for video in visible_videos:
                    try:
                        # 等待并查找包含 <a> 标签的元素
                        a_element = WebDriverWait(video, 10).until(
                            EC.presence_of_element_located((By.XPATH, './/a[contains(@href, "/video/BV")]'))
                        )

                        # 获取 <a> 标签的 href 属性
                        href = a_element.get_attribute('href')

                        # 提取 BV 号（如 BV1rA41147BN）
                        if '/video/' in href:
                            bv_number = href.split('/video/')[1].split('/')[0]

                            # 如果 BV 号已经在字典中，跳过这个 BV 号
                            if bv_number in self.video_dict:
                                continue

                            # 获取视频名称（从 <img> 标签的 alt 属性获取）
                            video_name = self.get_video_name(video)
                            # 获取视频时长
                            duration = self.get_video_duration(video)
                            # 获取视频封面URL
                            cover_url = self.get_video_cover_url(video)

                            # 将视频信息添加到字典
                            self.video_dict[bv_number] = {'name': video_name, 'duration': duration,
                                                          'cover_url': cover_url}
                            print(
                                f"找到视频: BV号: {bv_number}, 名称: {video_name}, 时长: {duration}, 封面: {cover_url}")

                    except Exception as e:
                        print(f"处理视频元素时出错: {e}")

            except Exception as e:
                print(f"查找视频元素时出错: {e}")

        print(f"搜索完成，共找到{len(self.video_dict)}个视频")
        return self.video_dict

    def get_video_name(self, video):
        """获取视频名称"""
        try:
            video_name = video.find_element(By.XPATH, './/img[@alt]').get_attribute('alt')
            return video_name if video_name else "未知"
        except NoSuchElementException:
            print("未找到视频名称")
            return "未知"

    def get_video_duration(self, video):
        """获取视频时长"""
        try:
            duration = video.find_element(By.CLASS_NAME, 'bili-video-card__stats__duration').text
            return duration if duration else "未知"
        except NoSuchElementException:
            print("未找到视频时长")
            return "未知"

    def get_video_cover_url(self, video):
        """获取视频封面URL"""
        try:
            cover_url = video.find_element(By.XPATH, './/img[@alt]').get_attribute('src')
            return cover_url if cover_url else "未知"
        except NoSuchElementException:
            print("未找到视频封面")
            return "未知"

    def fetch_video_page(self, url):
        """获取视频页面的HTML"""
        print(f"获取视频页面：{url}")
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"获取视频页面失败：{e}")
            return None

    def extract_video_info(self, html):
        """提取视频的音视频流信息"""
        print("提取视频信息...")
        try:
            obj = re.compile(r'window.__playinfo__=(.*?)</script>', re.S)
            json_str = obj.findall(html)[0]
            json_data = json.loads(json_str)
            video_url = json_data['data']['dash']['video'][0]['baseUrl']
            audio_url = json_data['data']['dash']['audio'][0]['baseUrl']
            return {'video_url': video_url, 'audio_url': audio_url}
        except (IndexError, KeyError, json.JSONDecodeError) as e:
            print(f"提取视频信息失败：{e}")
            return None

    def quit(self):
        """关闭浏览器驱动"""
        self.driver.quit()