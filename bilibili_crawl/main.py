import random
from bilibili_crawl.get_video_info import BilibiliVideoInfoFetcher
from download_merge import BilibiliVideoDownloader

def main():
    chromedriver_path = r'E:\tool\programe\chromedriver-win64\chromedriver.exe'
    ffmpeg_path = r'E:\tool\programe\ffmpeg-2024-08-26-git-98610fe95f-essentials_build\bin\ffmpeg.exe'
    output_file = r'output'

    fetcher = BilibiliVideoInfoFetcher(chromedriver_path)
    downloader = BilibiliVideoDownloader(ffmpeg_path)

    key_words = input("请输入你想查询的关键字：")
    order = input("请输入你要查询的类型（1.最多弹幕，2.最多播放，3.最新发布，4.最多收藏，5.综合排行）：")
    num = int(input("请输入你总共要查询的页数（一页24个视频）："))
    ran = input("是否随机下载（如果不随机则可以选定BV号下载，请输入'是'或者'否'）：")
    is_random = True if ran == '是' else False

    video_info_dict = fetcher.search_video_selenium(key_words, num, order)

    if is_random:
        video_num = int(input("你要下载的视频个数："))
        bvid_lst = random.sample(list(video_info_dict.keys()), min(video_num, len(video_info_dict)))
    else:
        print("\n找到以下视频：")
        for bv_id, info in video_info_dict.items():
            print(f"BV号: {bv_id}, 名称: {info['name']}, 时长: {info['duration']}, 封面: {info['cover_url']}")
        selected_bv_ids = input("请输入你要下载的BV号（多个BV号用逗号分隔）：").split(',')
        bvid_lst = [bv_id.strip() for bv_id in selected_bv_ids if bv_id.strip() in video_info_dict]

    for bv_id in bvid_lst:
        print(f"开始下载视频：{bv_id}")
        video_info = downloader.extract_video_info(fetcher.fetch_video_page(f'https://www.bilibili.com/video/{bv_id}/'))
        if video_info:
            video_info.update({'name': video_info_dict[bv_id]['name']})
            downloader.download_video_and_audio(bv_id, video_info, output_file)

    print("所有视频处理完成。")
    fetcher.quit()


if __name__ == "__main__":
    main()