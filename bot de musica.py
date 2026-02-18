import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque
import datetime
import time  


intents = discord.Intents.default()
intents.message_content = True 
intents.voice_states = True     
bot = commands.Bot(command_prefix='!', intents=intents)

fila_musicas = deque()
inicio_musica_atual = 0  
dados_musica_atual = None 

YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True', 'quiet': True}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2',
    'options': '-vn'
}

def formatar_tempo(segundos):
    return str(datetime.timedelta(seconds=int(segundos)))


class ControlesMusica(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸️ Pausar/Retomar", style=discord.ButtonStyle.grey)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Pausado!", ephemeral=True)
        elif vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Retomado!", ephemeral=True)

    @discord.ui.button(label="⏭️ Pular", style=discord.ButtonStyle.blurple)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client:
            self.ctx.voice_client.stop()
            await interaction.response.send_message("⏭️ Pulando!", ephemeral=True)


def criar_embed(dados, acao="Tocando agora", espera=None):
    cor = 0x71368a if acao == "Tocando agora" else 0x3498db
    embed = discord.Embed(title=dados['titulo'], url=dados['url_video'], color=cor)
    embed.set_author(name=acao)
    embed.set_thumbnail(url=dados['thumb'])
    embed.add_field(name="⏳ Duração", value=dados['duracao'], inline=True)
    embed.add_field(name="👤 Pedido por", value=dados['autor'], inline=True)
    
    if espera:
        embed.add_field(name="🕒 Espera estimada", value=espera, inline=False)
    
    embed.add_field(name="🎮 Comandos", value="`!p` Play | `!s` Skip | `!st` Stop", inline=False)
    embed.set_footer(text="Kiozuke Music • Controla pelos botões abaixo")
    return embed

def tocar_proxima(ctx):
    global inicio_musica_atual, dados_musica_atual
    if len(fila_musicas) > 0:
        dados = fila_musicas.popleft()
        source = discord.FFmpegOpusAudio(dados['url_audio'], **FFMPEG_OPTIONS)
        
        inicio_musica_atual = time.time()
        dados_musica_atual = dados
        
        ctx.voice_client.play(source, after=lambda e: tocar_proxima(ctx))
        asyncio.run_coroutine_threadsafe(ctx.send(embed=criar_embed(dados), view=ControlesMusica(ctx)), bot.loop)
    else:
        dados_musica_atual = None


@bot.command(aliases=['p'])
async def play(ctx, *, busca):
    global inicio_musica_atual, dados_musica_atual
    if not ctx.author.voice:
        return await ctx.send("❌ Precisas de entrar num canal de voz!")

    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()

    async with ctx.typing():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{busca}", download=False)['entries'][0]
            dados = {
                'url_audio': info['url'],
                'url_video': f"https://www.youtube.com/watch?v={info['id']}",
                'titulo': info['title'],
                'thumb': info['thumbnail'],
                'duracao_seg': info.get('duration', 0),
                'duracao': formatar_tempo(info.get('duration', 0)),
                'autor': ctx.author.display_name
            }

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            
            tempo_decorrido = time.time() - inicio_musica_atual
            if dados_musica_atual:
                falta_atual = max(0, dados_musica_atual['duracao_seg'] - tempo_decorrido)
            else:
                falta_atual = 0
            
            espera_fila = sum(m['duracao_seg'] for m in fila_musicas)
            total_espera = falta_atual + espera_fila
            
            fila_musicas.append(dados)
            await ctx.send(embed=criar_embed(dados, "Adicionado à fila", formatar_tempo(total_espera)), view=ControlesMusica(ctx))
        else:
            source = discord.FFmpegOpusAudio(dados['url_audio'], **FFMPEG_OPTIONS)
            inicio_musica_atual = time.time()
            dados_musica_atual = dados
            ctx.voice_client.play(source, after=lambda e: tocar_proxima(ctx))
            await ctx.send(embed=criar_embed(dados), view=ControlesMusica(ctx))

@bot.command(aliases=['st'])
async def stop(ctx):
    global dados_musica_atual
    if ctx.voice_client:
        fila_musicas.clear()
        dados_musica_atual = None
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ **Kiozuke parado e fila limpa!**")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, 
        name="!p | Kiozuke Music 🎶"
    ))
    print(f"✅ Kiozuke V3.0 Online!")


bot.run('SEU_TOKEN_AQUI')