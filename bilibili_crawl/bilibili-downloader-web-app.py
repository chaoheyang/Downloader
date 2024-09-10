from flask import Flask, render_template, request, jsonify
from bilibili_crawl.get_video_info import BilibiliVideoInfoFetcher
from download_merge import BilibiliVideoDownloader
import os
import threading

# 修改这里：指定模板文件夹的路径
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)

# Configuration
CHROMEDRIVER_PATH = r'E:\tool\programe\chromedriver-win64\chromedriver.exe'
FFMPEG_PATH = r'E:\tool\programe\ffmpeg-2024-08-26-git-98610fe95f-essentials_build\bin\ffmpeg.exe'
OUTPUT_DIR = r'output'

# Global variables for tracking download progress
download_progress = {}
download_lock = threading.Lock()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_videos():
    data = request.get_json()
    key_words = data['key_words']
    order = data['order']
    num = int(data['num'])

    fetcher = BilibiliVideoInfoFetcher(CHROMEDRIVER_PATH)
    try:
        video_info_dict = fetcher.search_video_selenium(key_words, num, order)
        return jsonify(video_info_dict)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        fetcher.quit()


@app.route('/download', methods=['POST'])
def download_videos():
    data = request.get_json()
    bvid_lst = data['bvid_lst']

    fetcher = BilibiliVideoInfoFetcher(CHROMEDRIVER_PATH)
    downloader = BilibiliVideoDownloader(FFMPEG_PATH)

    def download_thread():
        download_results = []
        for i, bv_id in enumerate(bvid_lst):
            try:
                app.logger.info(f"开始处理视频：{bv_id}")
                video_page = fetcher.fetch_video_page(f'https://www.bilibili.com/video/{bv_id}/')
                if not video_page:
                    raise ValueError("无法获取视频页面")

                video_info = downloader.extract_video_info(video_page)
                if not video_info:
                    raise ValueError("无法提取视频信息")

                app.logger.info(f"提取的视频信息：{video_info}")

                if bv_id not in fetcher.video_dict:
                    raise KeyError(f"BV号 {bv_id} 不在视频字典中")

                video_info.update({'name': fetcher.video_dict[bv_id]['name']})
                downloader.download_video_and_audio(bv_id, video_info, OUTPUT_DIR)
                download_results.append({'bv_id': bv_id, 'status': 'success'})
                app.logger.info(f"视频 {bv_id} 下载成功")

            except Exception as e:
                app.logger.exception(f"处理视频 {bv_id} 时出现错误")
                download_results.append({'bv_id': bv_id, 'status': 'failed', 'error': str(e)})

            finally:
                # Update progress
                with download_lock:
                    download_progress['current'] = i + 1
                    download_progress['total'] = len(bvid_lst)

        try:
            fetcher.quit()
        except Exception as e:
            app.logger.error(f"关闭fetcher时出错: {str(e)}")

        # Reset progress when done
        with download_lock:
            download_progress.clear()

        # 将下载结果保存到全局变量或数据库中
        app.config['DOWNLOAD_RESULTS'] = download_results

    # Start download in a separate thread
    threading.Thread(target=download_thread).start()

    return jsonify({'message': 'Download started'})

@app.route('/download_results', methods=['GET'])
def get_download_results():
    # 返回下载结果
    return jsonify(app.config.get('DOWNLOAD_RESULTS', []))


@app.route('/download_progress', methods=['GET'])
def get_download_progress():
    with download_lock:
        if 'current' in download_progress and 'total' in download_progress:
            progress = (download_progress['current'] / download_progress['total']) * 100
            return jsonify({'progress': progress})
        else:
            return jsonify({'progress': 0})


if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(debug=True)