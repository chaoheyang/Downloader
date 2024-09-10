import os
import re
import requests
import json


class BilibiliVideoDownloader:
    def __init__(self, ffmpeg_path):
        self.ffmpeg_path = ffmpeg_path
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': '',
            'Origin': 'https://www.bilibili.com',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'DNT': '1',
        }

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

    def download_file(self, url, filename, referer):
        """下载视频或音频文件"""
        self.headers['Referer'] = referer
        print(f"下载文件：{filename}")
        try:
            response = requests.get(url, headers=self.headers, stream=True)
            response.raise_for_status()
            with open(filename, mode='wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print(f"下载完成：{filename}")
        except requests.exceptions.RequestException as e:
            print(f"下载文件失败：{e}")

    def merge_audio_video(self, video_file, audio_file, output_file):
        """合并视频和音频文件"""
        print(f"合并视频和音频：{video_file} 和 {audio_file}")
        command = f'{self.ffmpeg_path} -i {video_file} -i {audio_file} -c:v copy -c:a aac {output_file} -y'
        try:
            os.system(command)
            print(f"合并完成，保存到：{output_file}")
            os.remove(video_file)
            os.remove(audio_file)
        except Exception as e:
            print(f"合并文件失败：{e}")

    def download_video_and_audio(self, bv_id, video_info, output_file):
        """下载视频和音频，并合并"""
        video_filename = f'{bv_id}_video.mp4'
        audio_filename = f'{bv_id}_audio.mp3'
        referer = f'https://www.bilibili.com/video/{bv_id}/'
        self.download_file(video_info['video_url'], video_filename, referer)
        self.download_file(video_info['audio_url'], audio_filename, referer)

        if os.path.exists(video_filename) and os.path.exists(audio_filename):
            video_name = video_info['name']
            sanitized_name = re.sub(r'[\\/*?:"<>|]', "", video_name)  # 去除文件名中的非法字符
            output_filepath = os.path.join(output_file, f'{sanitized_name}.mp4')
            self.merge_audio_video(video_filename, audio_filename, output_filepath)
        else:
            print(f"视频或音频文件下载失败，跳过合并：{video_filename} 和 {audio_filename}")