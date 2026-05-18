# -*- coding: utf-8 -*-
import yt_dlp

class ShortsExtractor:
    def __init__(self, quality="1080", max_results=15):
        self.max_results = max_results
        
        # Format based on quality setting
        if quality == "1080":
            video_format = 'best[height<=1080]'
        elif quality == "720":
            video_format = 'best[height<=720]'
        elif quality == "2160":
            video_format = 'best[height<=2160]'
        else:  # best
            video_format = 'best'
        
        self.ydl_opts = {
            'format': f'{video_format}+bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'playlistend': max_results,
            'ignoreerrors': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

    def get_shorts_list(self, source_type, search_term=None):
        video_list = []
        
        # Define search terms for different categories
        if source_type == "yt_shorts":
            search_terms = ["shorts trending", "#shorts"]
        elif source_type == "yt_music":
            search_terms = ["popular music videos", "top songs 2025"]
        elif source_type == "yt_trailers":
            search_terms = ["movie trailers official", "new movies 2025"]
        elif source_type == "yt_news":
            search_terms = ["breaking news today", "world news headlines"]
        elif source_type == "yt_gaming":
            search_terms = ["gaming shorts", "best gaming moments"]
        elif source_type == "yt_trending":
            search_terms = ["trending videos", "viral videos"]
        elif source_type == "yt_live":
            search_terms = ["live now", "live stream"]
        elif source_type == "yt_podcast":
            search_terms = ["podcast", "best podcasts"]
        elif source_type == "yt_new":
            search_terms = ["new uploads today", "fresh videos"]
        elif source_type == "search" and search_term:
            search_terms = [search_term]
        elif source_type == "yt_comedy":
            search_terms = ["funny videos fails", "stand up comedy", "comedy skits", "hilarious moments",
                            "fail compilation"]
        elif source_type == "yt_moviereviews":
            search_terms = ["movie review", "film criticism", "new movie review 2025", "best movies 2025",
                            "spoiler review"]
        elif source_type == "yt_educational":
            search_terms = ["educational videos", "how it works", "learn something new", "ted talk",
                            "interesting facts", "knowledge"]
        elif source_type == "yt_science":
            search_terms = ["science news", "space exploration", "physics explained", "latest discoveries",
                            "scientific breakthrough"]
        elif source_type == "yt_docs":
            search_terms = ["full documentary hd", "bbc documentary", "history documentary", "nature documentary",
                            "pbs documentary"]
        elif source_type == "yt_programming":
            search_terms = ["python tutorial", "coding tips", "web development", "programming basics",
                            "software engineering", "learn to code"]
        elif source_type == "yt_math":
            search_terms = ["mathematics explained", "physics concepts", "calculus tutorial", "algebra tricks",
                            "science experiments", "theoretical physics"]
        elif source_type == "yt_sports":
            search_terms = ["sports highlights today", "best moments", "sports news", "epic matches", "top 10 sports"]
        elif source_type == "yt_basketball":
            search_terms = ["nba highlights", "basketball best plays", "nba dunk contest", "basketball skills",
                            "lebron james", "steph curry"]
        elif source_type == "yt_football":
            search_terms = ["football highlights", "soccer best goals", "champions league", "football skills",
                            "messi highlights", "ronaldo goals"]
        elif source_type == "yt_fitness":
            search_terms = ["workout routine", "home gym", "fitness tips", "weight training", "cardio workout",
                            "bodybuilding"]
        elif source_type == "yt_art":
            search_terms = ["art tutorial", "drawing tips", "painting techniques", "creative art", "digital art",
                            "sketching"]
        elif source_type == "yt_diy":
            search_terms = ["diy projects", "home improvement", "woodworking", "handmade crafts", "life hacks",
                            "upcycling"]
        elif source_type == "yt_cooking":
            search_terms = ["easy recipes", "cooking tutorial", "quick meals", "healthy cooking", "delicious food",
                            "kitchen hacks"]
        elif source_type == "yt_tech":
            search_terms = ["tech review", "new gadgets", "smartphone review", "laptop review", "latest tech",
                            "apple vs samsung"]
        elif source_type == "yt_cars":
            search_terms = ["car review", "new cars 2025", "supercars", "test drive", "auto show", "car comparison"]
        elif source_type == "yt_travel":
            search_terms = ["travel vlog", "amazing places", "travel guide", "best destinations", "travel tips",
                            "adventure travel"]
        elif source_type == "yt_animals":
            search_terms = ["cute animals", "funny pets", "wildlife documentary", "animal rescue", "dog videos",
                            "cat videos"]
        elif source_type == "channel" and search_term:
            return self.extract_channel_videos(search_term)
        elif source_type == "live_channel" and search_term:
            return self.extract_live_channel(search_term)
        else:
            return video_list

        for term in search_terms:
            try:
                url = f"ytsearch{self.max_results}:{term}"
                print(f"[CiefpYouTube] Searching: {term}")
                
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    if info and 'entries' in info:
                        for entry in info['entries']:
                            if entry and entry.get('title'):
                                video_url = entry.get('url')
                                if not video_url and entry.get('id'):
                                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                                
                                if video_url:
                                    video_list.append({
                                        'title': entry.get('title', 'No title')[:100],
                                        'url': video_url,
                                        'author': entry.get('uploader', 'Unknown') or 'Unknown'
                                    })
                                    print(f"[CiefpYouTube] + {entry.get('title', 'Unknown')[:50]}")
                                    
                                    if len(video_list) >= self.max_results:
                                        break
                    if len(video_list) >= self.max_results:
                        break
                        
            except Exception as e:
                print(f"[CiefpYouTube] Error: {str(e)[:100]}")
                continue
        
        print(f"[CiefpYouTube] Found: {len(video_list)} videos")
        return video_list

    def extract_channel_videos(self, channel_url):
        video_list = []

        try:
            videos_url = channel_url.rstrip('/') + '/videos'

            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(videos_url, download=False)

                if info and 'entries' in info:
                    for entry in info['entries'][:self.max_results]:
                        if not entry:
                            continue

                        video_url = entry.get('url')
                        if entry.get('id'):
                            video_url = f"https://www.youtube.com/watch?v={entry['id']}"

                        video_list.append({
                            'title': entry.get('title', 'No title')[:100],
                            'url': video_url,
                            'author': entry.get('uploader', '')
                        })

        except Exception as e:
            print(f"Channel extraction error: {e}")

        return video_list

    def extract_live_channel(self, channel_url):
        video_list = []

        try:

            urls_to_try = []

            # 1. prvo original URL iz JSON
            urls_to_try.append(channel_url.rstrip('/'))

            # 2. fallback /live
            if "/live" not in channel_url:
                urls_to_try.append(channel_url.rstrip('/') + "/live")

            # 3. fallback /streams
            if "/streams" not in channel_url:
                urls_to_try.append(channel_url.rstrip('/') + "/streams")

            print(f"[CiefpYouTube] LIVE TRY URLS: {urls_to_try}")

            for test_url in urls_to_try:

                try:
                    print(f"[CiefpYouTube] TRY: {test_url}")

                    with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                        info = ydl.extract_info(test_url, download=False)

                    if not info:
                        continue

                    # direktan LIVE stream
                    if info.get('_type') != 'playlist':

                        video_url = (
                                info.get('webpage_url')
                                or info.get('url')
                        )

                        if video_url:
                            video_list.append({
                                'title': info.get('title', 'LIVE')[:100],
                                'url': video_url,
                                'author': info.get('uploader', 'LIVE')
                            })

                            print(f"[CiefpYouTube] LIVE DIRECT OK")
                            return video_list

                    # streams lista
                    elif 'entries' in info:

                        for entry in info['entries']:

                            if not entry:
                                continue

                            if (
                                    entry.get('live_status') == 'is_live'
                                    or entry.get('is_live')
                            ):

                                video_url = entry.get('url')

                                if entry.get('id'):
                                    video_url = (
                                        f"https://www.youtube.com/watch?v={entry['id']}"
                                    )

                                video_list.append({
                                    'title': entry.get('title', 'LIVE')[:100],
                                    'url': video_url,
                                    'author': entry.get('uploader', 'LIVE')
                                })

                                print(f"[CiefpYouTube] LIVE STREAM FOUND")
                                return video_list

                except Exception as e:
                    print(f"[CiefpYouTube] TRY FAILED: {test_url}")
                    print(str(e))

                    continue

        except Exception as e:
            print(f"[CiefpYouTube] Live extraction error: {e}")

        return video_list
