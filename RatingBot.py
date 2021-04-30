import os
import discord
import pymysql
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv


def GetRatingValue(reaction):
    reaction = str(str(reaction).encode('unicode-escape'))
    if reaction == r"b'1\\ufe0f\\u20e3'" or reaction == '1':
        return 1
    if reaction == r"b'2\\ufe0f\\u20e3'" or reaction == '2':
        return 2
    if reaction == r"b'3\\ufe0f\\u20e3'" or reaction == '3':
        return 3
    if reaction == r"b'4\\ufe0f\\u20e3'" or reaction == '4':
        return 4
    if reaction == r"b'5\\ufe0f\\u20e3'" or reaction == '5':
        return 5
    if reaction == r"b'6\\ufe0f\\u20e3'" or reaction == '6':
        return 6
    if reaction == r"b'7\\ufe0f\\u20e3'" or reaction == '7':
        return 7
    if reaction == r"b'8\\ufe0f\\u20e3'" or reaction == '8':
        return 8
    if reaction == r"b'9\\ufe0f\\u20e3'" or reaction == '9':
        return 9
    if reaction == r"b'\\U0001f51f'" or reaction == '10':
        return 10
    return 0


# region SQL


def WriteToTable(user, rating):
    print(f'Writing user {user} value {rating}')
    conn = pymysql.connect(host=ENDPOINT,
                           user=USR,
                           password=PASSWORD,
                           port=PORT,
                           database=DBNAME)

    cursor = conn.cursor()

    sql = f'''
    INSERT INTO ratings (
        user,
        rating
    )
    VALUES (
        (select user_id from discord.users where user = '{str(user).split('#')[0]}'),
        {rating}
    );
    '''
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()
    print(f'Wrote user {user} value {rating} to db')


def GetCurrentRating(user):
    username = str(user).split('#')[0]

    print(f'Getting rating for {username}')
    conn = pymysql.connect(host=ENDPOINT,
                           user=USR,
                           password=PASSWORD,
                           port=PORT,
                           database=DBNAME)

    cursor = conn.cursor()

    sql = f'''
SELECT AVG(r.rating)
FROM discord.users u
JOIN discord.ratings r on u.user_id = r.user
WHERE u.user = '{username}'
    '''

    cursor.execute(sql)
    data = cursor.fetchone()

    if data[0] is None:
        return 'None'

    cursor.close()
    conn.close()

    return round(data[0], 2)


# endregion

# region Spotify


def GetSpotifyCreds():
    f = open('SpotifyCreds.txt')
    for line in f.readlines():
        varName = line.split('=', 1)[0]
        if varName == 'CLIENT_ID':
            CLIENT_ID = line.split('=', 1)[1].strip('\n')
        if varName == 'CLIENT_SECRET':
            CLIENT_SECRET = line.split('=', 1)[1].strip('\n')
        if varName == 'PLAYLIST_ID':
            PLAYLIST_ID = line.split('=', 1)[1].strip('\n')
    return CLIENT_ID, CLIENT_SECRET, PLAYLIST_ID


def AddToMusicalChairs(spotifyLink):
    track = spotify.track(spotifyLink)
    spotify.playlist_add_items(PLAYLIST_ID, [track["uri"]])


def RatingComplete(reaction):
    guild = client.get_guild(reaction.message.guild.id)
    return len(reaction.message.reactions) == len(guild.members) - 1


def RemoveSongFromPlaylist(spotifyLink):
    track = spotify.track(spotifyLink)
    spotify.playlist_remove_all_occurrences_of_items(PLAYLIST_ID, [track["uri"]])


CLIENT_ID, CLIENT_SECRET, PLAYLIST_ID = GetSpotifyCreds()
spotify = spotipy.Spotify(
    auth_manager=SpotifyOAuth(scope='playlist-modify-public',
                              username='mishoal11',
                              client_id=CLIENT_ID,
                              client_secret=CLIENT_SECRET,
                              redirect_uri='http://localhost:8888/callback/')
)


# endregion


# region Discord

def GetDiscordCreds():
    f = open('DiscordCreds.txt')
    for line in f.readlines():
        varName = line.split('=', 1)[0]
        if varName == 'ENDPOINT':
            ENDPOINT = line.split('=', 1)[1].strip('\n')
        if varName == 'PORT':
            PORT = int(line.split('=', 1)[1])
        if varName == 'DBNAME':
            DBNAME = line.split('=', 1)[1].strip('\n')
        if varName == 'USR':
            USR = line.split('=', 1)[1].strip('\n')
        if varName == 'PASSWORD':
            PASSWORD = line.split('=', 1)[1].strip('\n')
    return ENDPOINT, PORT, DBNAME, USR, PASSWORD


ENDPOINT, PORT, DBNAME, USR, PASSWORD = GetDiscordCreds()

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

print('Creating Client')
intents = discord.Intents.all()
client = discord.Client(intents=intents)
print(f'Client: {client}')


@client.event
async def on_message(message):
    print(message.guild.id)
    if message.author == client.user:
        return

    #TODO get nicknames
    if '!ratings' in message.content:
        guild = client.get_guild(message.guild.id)
        for user in [member.name for member in guild.members]:
            print(f'Checking user: {user}')
            username = str(user).split('#')[0]
            await message.channel.send(f'{username} - {GetCurrentRating(username)}')
            print(f'{username} - {GetCurrentRating(user)}')

    if '!help' in message.content:
        await message.channel.send('''
Type "!ratings" to display each user.
Use the number emojis to rate song postings.''')

    if 'open.spotify' in message.content:
        print('Spotify link detected')
        AddToMusicalChairs(message.content)


@client.event
async def on_reaction_add(reaction, user):

    # Only respond to spotify postings
    if 'open.spotify' not in reaction.message.content:
        return

    rating = GetRatingValue(reaction)
    if rating == 0:
        await reaction.message.channel.send('Rating not recognized')
        return

    # ensure rating is not from poster
    if user.name == reaction.message.author.name:
        await reaction.message.channel.send('Do *not* rate your own song')
        return

    WriteToTable(reaction.message.author.name, rating)

    if RatingComplete(reaction):
        print('Rating complete')
        RemoveSongFromPlaylist(reaction.message.content)


@client.event
async def on_user_update(before, after):
    # TODO Update db vals if names change
    print('User profile updated')

client.run(TOKEN)


# endregion