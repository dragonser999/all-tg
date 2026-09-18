require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');

const token = process.env.BOT_TOKEN;

if (!token) {
    console.error("ERROR: BOT_TOKEN is missing!");
    process.exit(1);
}

const bot = new TelegramBot(token, { polling: true });

console.log("Custom Downloader Telegram Bot Started...");

// In-Memory Storage for Session Data
const userSessions = new Map();

// Standard Headers
const commonHeaders = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
};

// 1. YouTube Fetcher
async function fetchYouTube(url) {
    const res = await axios.get(`https://yt-api-s2tl.vercel.app/api/yt-download?url=${encodeURIComponent(url)}`, { timeout: 25000 });
    return res.data;
}

// 2. Facebook Fetcher
async function fetchFacebook(url) {
    const res = await axios.get(`https://fb-api-cyan.vercel.app/api/fb-download?url=${encodeURIComponent(url)}`, { timeout: 25000 });
    return res.data;
}

// 3. TeraBox Fetcher
async function fetchTerabox(url) {
    const res = await axios.get(`https://terabox-api-psi-navy.vercel.app/api/terabox-download?url=${encodeURIComponent(url)}`, { timeout: 25000 });
    return res.data;
}

// 4. Spotify Fetcher
async function fetchSpotify(url) {
    const res = await axios.get(`https://spotify-api-five-beige.vercel.app/api/spotify-download?url=${encodeURIComponent(url)}`, { timeout: 25000 });
    return res.data;
}

// 5. Instagram Fetcher (ContentStudio API)
async function fetchInstagram(url) {
    const res = await axios.post(
        'https://api-free-tools.contentstudio.io/api/v1/video/facebook',
        { url: url },
        {
            headers: {
                ...commonHeaders,
                'Content-Type': 'application/json',
                'Origin': 'https://contentstudio.io',
                'Referer': 'https://contentstudio.io/'
            },
            timeout: 25000
        }
    );
    return res.data;
}

// Start Command Message
bot.onText(/\/start/, (msg) => {
    const startText = `👋 *Welcome to All-in-One Custom Downloader Bot!*\n\n` +
        `I support downloading media from the following platforms:\n\n` +
        `🎬 *YouTube Downloader* (MP4 & M4A Audio support)\n` +
        `📘 *Facebook Downloader* (HD & SD Quality support)\n` +
        `📹 *TeraBox Downloader* (Direct Stream & Fast Download links)\n` +
        `🎵 *Spotify Downloader* (Tracks & Albums support)\n` +
        `📸 *Instagram Downloader* (Reels & Video support)\n\n` +
        `_Send me any supported link to get started!_`;

    bot.sendMessage(msg.chat.id, startText, { parse_mode: "Markdown" });
});

// Handling Link Received
bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;

    if (!text || text.startsWith('/')) return;

    // Detect Platforms
    const isYT = /(youtube\.com|youtu\.be)/i.test(text);
    const isFB = /(facebook\.com|fb\.watch)/i.test(text);
    const isTera = /(terabox|1024terabox|teraboxapp|freeterabox)\.com/i.test(text);
    const isSpotify = /spotify\.com/i.test(text);
    const isInsta = /(instagram\.com|instagr\.am)/i.test(text);

    if (!isYT && !isFB && !isTera && !isSpotify && !isInsta) {
        return bot.sendMessage(chatId, "❌ Unsupported link. Please send a valid YouTube, Facebook, TeraBox, Spotify, or Instagram link.");
    }

    const sessionId = `${chatId}_${Date.now()}`;

    // --- YOUTUBE ---
    if (isYT) {
        const statusMsg = await bot.sendMessage(chatId, "🔄 *Fetching YouTube details...*", { parse_mode: "Markdown" });
        try {
            const data = await fetchYouTube(text);
            if (data && (data.status || data.result)) {
                userSessions.set(sessionId, data);
                await bot.deleteMessage(chatId, statusMsg.message_id);
                return bot.sendMessage(chatId, `🎬 *${data.title || data.result?.title || "YouTube Media"}*\n\nSelect a format:`, {
                    parse_mode: "Markdown",
                    reply_markup: {
                        inline_keyboard: [
                            [
                                { text: "🎥 MP4 (Video)", callback_data: `yt_mp4|${sessionId}` },
                                { text: "🎵 M4A (Audio)", callback_data: `yt_m4a|${sessionId}` }
                            ]
                        ]
                    }
                });
            } else {
                return bot.editMessageText("❌ Unable to find YouTube details.", { chat_id: chatId, message_id: statusMsg.message_id });
            }
        } catch (e) {
            return bot.editMessageText("⚠️ YouTube API Error occurred.", { chat_id: chatId, message_id: statusMsg.message_id });
        }
    }

    // --- FACEBOOK ---
    if (isFB) {
        const statusMsg = await bot.sendMessage(chatId, "🔄 *Fetching Facebook details...*", { parse_mode: "Markdown" });
        try {
            const data = await fetchFacebook(text);
            if (data && (data.status || data.result)) {
                userSessions.set(sessionId, data);
                await bot.deleteMessage(chatId, statusMsg.message_id);
                
                const buttons = [];
                const res = data.result || data;
                if (res.hd || res.hd_url) buttons.push({ text: "🎬 HD Video", callback_data: `fb_hd|${sessionId}` });
                if (res.sd || res.sd_url) buttons.push({ text: "📱 SD Video", callback_data: `fb_sd|${sessionId}` });

                if (buttons.length === 0 && (res.url || res.download_url)) {
                    buttons.push({ text: "🎥 Download Video", callback_data: `fb_sd|${sessionId}` });
                }

                return bot.sendMessage(chatId, `📘 *Facebook Video*\n\nSelect video quality:`, {
                    parse_mode: "Markdown",
                    reply_markup: { inline_keyboard: [buttons] }
                });
            } else {
                return bot.editMessageText("❌ Facebook video not available.", { chat_id: chatId, message_id: statusMsg.message_id });
            }
        } catch (e) {
            return bot.editMessageText("⚠️ Facebook API Error occurred.", { chat_id: chatId, message_id: statusMsg.message_id });
        }
    }

    // --- TERABOX ---
    if (isTera) {
        const statusMsg = await bot.sendMessage(chatId, "🔄 *Fetching TeraBox details...*", { parse_mode: "Markdown" });
        try {
            const data = await fetchTerabox(text);
            if (data && (data.status || data.ok)) {
                userSessions.set(sessionId, data);
                await bot.deleteMessage(chatId, statusMsg.message_id);

                const file = data.result?.[0] || data.files?.[0] || data;
                const title = file.file_name || file.name || data.title || "TeraBox File";
                const size = file.file_size || file.size_str || data.size_str || "N/A";

                return bot.sendMessage(chatId, `📦 *${title}*\n📐 Size: *${size}*\n\nSelect an option:`, {
                    parse_mode: "Markdown",
                    reply_markup: {
                        inline_keyboard: [
                            [
                                { text: "▶️ Stream Link", callback_data: `tera_stream|${sessionId}` },
                                { text: "📥 Download Link", callback_data: `tera_download|${sessionId}` }
                            ],
                            [
                                { text: "📤 Send File Directly", callback_data: `tera_send|${sessionId}` }
                            ]
                        ]
                    }
                });
            } else {
                return bot.editMessageText("❌ Could not fetch TeraBox file details.", { chat_id: chatId, message_id: statusMsg.message_id });
            }
        } catch (e) {
            return bot.editMessageText("⚠️ TeraBox API Error occurred.", { chat_id: chatId, message_id: statusMsg.message_id });
        }
    }

    // --- SPOTIFY ---
    if (isSpotify) {
        const statusMsg = await bot.sendMessage(chatId, "🔄 *Fetching Spotify details...*", { parse_mode: "Markdown" });
        try {
            const data = await fetchSpotify(text);
            const tracks = data.result || data.tracks || (Array.isArray(data) ? data : [data]);

            if (tracks && tracks.length > 0) {
                await bot.editMessageText(`🎵 *Found ${tracks.length} track(s)! Sending...*`, { chat_id: chatId, message_id: statusMsg.message_id, parse_mode: "Markdown" });

                for (const track of tracks) {
                    const audioUrl = track.download_url || track.url || track.link;
                    const caption = `🎵 *${track.title || track.name || "Spotify Track"}*\n👤 *${track.artist || track.artists || ""}*`;
                    if (audioUrl) {
                        await bot.sendAudio(chatId, audioUrl, { caption: caption, parse_mode: "Markdown" });
                    }
                }
                await bot.deleteMessage(chatId, statusMsg.message_id);
            } else {
                await bot.editMessageText("❌ Could not fetch Spotify audio.", { chat_id: chatId, message_id: statusMsg.message_id });
            }
        } catch (e) {
            return bot.editMessageText("⚠️ Spotify API Error occurred.", { chat_id: chatId, message_id: statusMsg.message_id });
        }
    }

    // --- INSTAGRAM ---
    if (isInsta) {
        const statusMsg = await bot.sendMessage(chatId, "🔄 *Fetching Instagram media...*", { parse_mode: "Markdown" });
        try {
            const data = await fetchInstagram(text);
            if (data && data.url) {
                await bot.editMessageText("📥 *Sending video...*", { chat_id: chatId, message_id: statusMsg.message_id, parse_mode: "Markdown" });
                await bot.sendVideo(chatId, data.url, { caption: "✅ *Instagram Video*", parse_mode: "Markdown" });
                await bot.deleteMessage(chatId, statusMsg.message_id);
            } else {
                await bot.editMessageText("❌ Instagram video not found.", { chat_id: chatId, message_id: statusMsg.message_id });
            }
        } catch (e) {
            return bot.editMessageText("⚠️ Instagram API Error occurred.", { chat_id: chatId, message_id: statusMsg.message_id });
        }
    }
});

// Inline Buttons Callback Listener
bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const [type, sessionId] = query.data.split('|');
    const data = userSessions.get(sessionId);

    bot.answerCallbackQuery(query.id);

    if (!data) {
        return bot.sendMessage(chatId, "❌ Session expired. Please send the link again.");
    }

    const res = data.result || data.files?.[0] || data;

    // YouTube Video / Audio
    if (type === 'yt_mp4' || type === 'yt_m4a') {
        const isVideo = type === 'yt_mp4';
        const mediaUrl = isVideo ? (res.mp4 || res.video_url || res.download_url) : (res.m4a || res.mp3 || res.audio_url);
        
        if (!mediaUrl) return bot.sendMessage(chatId, "❌ Download link not available.");

        const status = await bot.sendMessage(chatId, `⏳ *Sending YouTube ${isVideo ? 'Video' : 'Audio'}...*`, { parse_mode: "Markdown" });
        try {
            if (isVideo) {
                await bot.sendVideo(chatId, mediaUrl, { caption: `🎬 *${data.title || "YouTube Video"}*`, parse_mode: "Markdown" });
            } else {
                await bot.sendAudio(chatId, mediaUrl, { caption: `🎵 *${data.title || "YouTube Audio"}*`, parse_mode: "Markdown" });
            }
            await bot.deleteMessage(chatId, status.message_id);
        } catch (e) {
            await bot.editMessageText(`⚠️ Could not send file directly (likely exceeds Telegram bot upload limits).\n\n🔗 [Click here to Download Directly](${mediaUrl})`, {
                chat_id: chatId,
                message_id: status.message_id,
                parse_mode: "Markdown"
            });
        }
    }

    // Facebook HD / SD
    if (type === 'fb_hd' || type === 'fb_sd') {
        const isHd = type === 'fb_hd';
        const mediaUrl = isHd ? (res.hd || res.hd_url) : (res.sd || res.sd_url || res.url);

        if (!mediaUrl) return bot.sendMessage(chatId, "❌ Video link not available.");

        const status = await bot.sendMessage(chatId, `⏳ *Sending Facebook ${isHd ? 'HD' : 'SD'} Video...*`, { parse_mode: "Markdown" });
        try {
            await bot.sendVideo(chatId, mediaUrl, { caption: `📘 *Facebook Video (${isHd ? 'HD' : 'SD'})*`, parse_mode: "Markdown" });
            await bot.deleteMessage(chatId, status.message_id);
        } catch (e) {
            await bot.editMessageText(`⚠️ Could not send video file directly.\n\n🔗 [Click here to Download Directly](${mediaUrl})`, {
                chat_id: chatId,
                message_id: status.message_id,
                parse_mode: "Markdown"
            });
        }
    }

    // TeraBox Handling
    if (type === 'tera_stream') {
        const streamUrl = res.stream_url || res.stream || data.stream_url;
        bot.sendMessage(chatId, `▶️ *TeraBox Stream Link:*\n\n${streamUrl}`, { parse_mode: "Markdown" });
    }

    if (type === 'tera_download') {
        const downloadUrl = res.download_url || res.download || data.download_url || res.stream_url;
        bot.sendMessage(chatId, `📥 *TeraBox Fast Download Link:*\n\n${downloadUrl}`, { parse_mode: "Markdown" });
    }

    if (type === 'tera_send') {
        const fileUrl = res.download_url || res.stream_url || data.stream_url;
        const status = await bot.sendMessage(chatId, "⏳ *Sending TeraBox file... (Large files may take longer)*", { parse_mode: "Markdown" });
        try {
            await bot.sendVideo(chatId, fileUrl, { caption: `📦 *${res.file_name || res.name || "TeraBox File"}*`, parse_mode: "Markdown" });
            await bot.deleteMessage(chatId, status.message_id);
        } catch (e) {
            await bot.editMessageText(`⚠️ Could not send file directly via Telegram (due to Telegram upload limit or timeout).\n\n🔗 [Click here to Download Directly](${fileUrl})`, {
                chat_id: chatId,
                message_id: status.message_id,
                parse_mode: "Markdown"
            });
        }
    }
});
