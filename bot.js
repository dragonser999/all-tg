require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');

const token = process.env.BOT_TOKEN;

if (!token) {
    console.error("ERROR: BOT_TOKEN is missing!");
    process.exit(1);
}

const bot = new TelegramBot(token, { polling: true });

console.log("All-in-One Downloader Bot Online...");

const commonHeaders = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
};

// 1. TeraBox Handler
async function handleTerabox(text) {
    const res = await axios.post('https://teraplayer-xfwi.onrender.com/api/preview', 
        { url: text, password: "" }, 
        { headers: { ...commonHeaders, 'Content-Type': 'application/json' }, timeout: 25000 }
    );
    if (res.data && res.data.ok) {
        const file = res.data.files?.[0] || res.data;
        return {
            type: 'video',
            url: file.stream_url || file.download_url,
            caption: `📹 *${file.name || res.data.title || "TeraBox File"}*\n📦 Size: ${file.size_str || res.data.size_str || "N/A"}`
        };
    }
    return null;
}

// 2. Instagram & Facebook Handler (ContentStudio Proxy)
async function handleSocialVideo(text) {
    const res = await axios.post('https://api-free-tools.contentstudio.io/api/v1/video/facebook', 
        { url: text }, 
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
    if (res.data && res.data.url) {
        return {
            type: 'video',
            url: res.data.url,
            caption: `✅ *Media Downloaded Successfully*`
        };
    }
    return null;
}

// 3. Pinterest Handler
async function handlePinterest(text) {
    const res = await axios.get(`https://pingrab.app/api/pinterest?url=${encodeURIComponent(text)}`, { headers: commonHeaders, timeout: 20000 });
    if (res.data && res.data.url) {
        return {
            type: res.data.is_video ? 'video' : 'photo',
            url: res.data.url,
            caption: `📌 *Pinterest Media*`
        };
    }
    return null;
}

// 4. Spotify Handler (Track / Album)
async function handleSpotify(text) {
    const res = await axios.post('https://musicfab.io/api/spotify/download', 
        { url: text }, 
        { headers: { ...commonHeaders, 'Content-Type': 'application/json' }, timeout: 25000 }
    );
    if (res.data && res.data.audio_url) {
        return {
            type: 'audio',
            url: res.data.audio_url,
            caption: `🎵 *${res.data.title || "Spotify Track"}* - ${res.data.artist || ""}`
        };
    }
    return null;
}

// 5. YouTube Handler (Convert via Service API)
async function handleYouTube(url, type) {
    const res = await axios.get(`https://spotsaver.net/api/yt?url=${encodeURIComponent(url)}&type=${type}`, { headers: commonHeaders, timeout: 30000 });
    if (res.data && res.data.download_url) {
        return {
            type: type === 'mp3' ? 'audio' : 'video',
            url: res.data.download_url,
            caption: `▶️ *${res.data.title || "YouTube Media"}*`
        };
    }
    return null;
}

// Start Command
bot.onText(/\/start/, (msg) => {
    bot.sendMessage(
        msg.chat.id,
        `👋 *All-in-One Downloader Bot-ലേക്ക് സ്വാഗതം!*\n\nതാഴെ പറയുന്ന ഏത് ലിങ്കും അയക്കാം:\n\n• *YouTube* (MP3/MP4 Buttons)\n• *Instagram & Facebook* Videos/Reels\n• *Spotify* Tracks & Albums\n• *TeraBox* Files\n• *Pinterest* Media\n\n_ഏതെങ്കിലും ഒരു ലിങ്ക് അയക്കൂ!_`,
        { parse_mode: "Markdown" }
    );
});

// Handling Link Processing
bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;

    if (!text || text.startsWith('/')) return;

    // Detect YouTube
    const isYouTube = /(youtube\.com|youtu\.be)/i.test(text);
    if (isYouTube) {
        return bot.sendMessage(chatId, "🎬 *YouTube Format തെരഞ്ഞെടുക്കൂ:*", {
            parse_mode: "Markdown",
            reply_markup: {
                inline_keyboard: [
                    [
                        { text: "🎵 MP3 (Audio)", callback_data: `yt_mp3|${text}` },
                        { text: "🎥 MP4 (Video)", callback_data: `yt_mp4|${text}` }
                    ]
                ]
            }
        });
    }

    // Other Platforms
    const isTerabox = /(terabox|1024terabox|teraboxapp|freeterabox)\.com/i.test(text);
    const isSocial = /(instagram\.com|instagr\.am|facebook\.com|fb\.watch)/i.test(text);
    const isPinterest = /(pinterest\.com|pin\.it)/i.test(text);
    const isSpotify = /spotify\.com/i.test(text);

    if (!isTerabox && !isSocial && !isPinterest && !isSpotify) {
        return bot.sendMessage(chatId, "❌ പിന്തുണയ്ക്കാത്ത ലിങ്ക് ആണ്. സപ്പോർട്ട് ചെയ്യുന്ന മറ്റ് ലിങ്കുകൾ അയക്കൂ.");
    }

    const statusMsg = await bot.sendMessage(chatId, "🔄 *Media Extract ചെയ്യുന്നു...*", { parse_mode: "Markdown" });

    try {
        let result = null;

        if (isTerabox) result = await handleTerabox(text);
        else if (isSocial) result = await handleSocialVideo(text);
        else if (isPinterest) result = await handlePinterest(text);
        else if (isSpotify) result = await handleSpotify(text);

        if (result && result.url) {
            await bot.editMessageText("📥 *മീഡിയ അയക്കുന്നു...*", { chat_id: chatId, message_id: statusMsg.message_id });

            if (result.type === 'video') await bot.sendVideo(chatId, result.url, { caption: result.caption, parse_mode: "Markdown" });
            else if (result.type === 'audio') await bot.sendAudio(chatId, result.url, { caption: result.caption, parse_mode: "Markdown" });
            else if (result.type === 'photo') await bot.sendPhoto(chatId, result.url, { caption: result.caption, parse_mode: "Markdown" });

            await bot.deleteMessage(chatId, statusMsg.message_id);
        } else {
            await bot.editMessageText("❌ ഡൗൺലോഡ് ലിങ്ക് ലഭിച്ചില്ല. ലിങ്ക് വാലിഡ് ആണോ എന്ന് പരിശോധിക്കുക.", { chat_id: chatId, message_id: statusMsg.message_id });
        }
    } catch (err) {
        console.error(err.message);
        await bot.editMessageText("⚠️ എറർ സംഭവിച്ചു. അല്പം കഴിഞ്ഞ് വീണ്ടും ശ്രമിക്കുക.", { chat_id: chatId, message_id: statusMsg.message_id });
    }
});

// Handling YouTube Button Clicks
bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const [action, url] = query.data.split('|');

    if (action === 'yt_mp3' || action === 'yt_mp4') {
        const type = action === 'yt_mp3' ? 'mp3' : 'mp4';
        bot.answerCallbackQuery(query.id, { text: `Processing ${type.toUpperCase()}...` });

        const statusMsg = await bot.sendMessage(chatId, `⏳ *YouTube ${type.toUpperCase()} ഡൗൺലോഡ് ചെയ്യുന്നു...*`, { parse_mode: "Markdown" });

        try {
            const result = await handleYouTube(url, type);
            if (result && result.url) {
                if (type === 'mp3') {
                    await bot.sendAudio(chatId, result.url, { caption: result.caption, parse_mode: "Markdown" });
                } else {
                    await bot.sendVideo(chatId, result.url, { caption: result.caption, parse_mode: "Markdown" });
                }
                await bot.deleteMessage(chatId, statusMsg.message_id);
            } else {
                await bot.editMessageText("❌ YouTube ഡൗൺലോഡ് പരാജയപ്പെട്ടു.", { chat_id: chatId, message_id: statusMsg.message_id });
            }
        } catch (err) {
            console.error(err.message);
            await bot.editMessageText("⚠️ പ്രോസസ്സ് ചെയ്യുന്നതിൽ എറർ സംഭവിച്ചു.", { chat_id: chatId, message_id: statusMsg.message_id });
        }
    }
});
