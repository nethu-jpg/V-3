import os
import logging
import random
import asyncio
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait, UserAlreadyParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from database.ia_filterdb import Media, get_file_details, unpack_new_file_id
from database.users_chats_db import db
from info import CHANNELS, ADMINS, AUTH_CHANNEL, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION, PROTECT_CONTENT
from utils import get_settings, get_size, is_subscribed, save_group_settings, temp
from database.connections_mdb import active_connection
import re
import json
import base64
import re
import asyncio



from user import User
from info import AUTH_USERS, DOC_SEARCH, VID_SEARCH, MUSIC_SEARCH
from database.mdb import (
    savefiles,
    deletefiles,
    deletegroupcol,
    channelgroup,
    ifexists,
    deletealldetails,
    findgroupid,
    channeldetails,
    countfilters
)

logger = logging.getLogger(__name__)

BATCH_FILES = {}

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [
            [
                InlineKeyboardButton('❓ Help', url=f"https://t.me/{temp.U_NAME}?start=help")
            ]
            ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(script.START_TXT.format(message.from_user.mention if message.from_user else message.chat.title, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup)
        await asyncio.sleep(2) # wait a bit, before checking.
        if not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, "Unknown"))       
            await db.add_chat(message.chat.id, message.chat.title)
        return 
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))
    if len(message.command) != 2:
        buttons = [[
            InlineKeyboardButton('➕ Add Me To Your Group ➕', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
            ],[
            InlineKeyboardButton('❓ Help', callback_data='help'),
            InlineKeyboardButton('ℹ️ About', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

        
        
        




#@Client.on_message(filters.group & filters.command(['fadd']) & filters.incoming)
#@Client.on_message(filters.group & filters.command(["fadd"]))
@Client.on_message(filters.command("fadd") & filters.incoming)
async def addchannel(client: Bot, message: Message):

    if message.from_user.id not in AUTH_USERS:
        return

    try:
        cmd, text = message.text.split(" ", 1)
    except:
        await message.reply_text(
            "<i>Enter in correct format!\n\n<code>/add channelid</code>  or\n"
            "<code>/add @channelusername</code></i>"
            "\n\nGet Channel id from @ChannelidHEXbot",
        )
        return
    try:
        if not text.startswith("@"):
            chid = int(text)
            if not len(text) == 14:
                await message.reply_text(
                    "Enter valid channel ID"
                )
                return
        elif text.startswith("@"):
            chid = text
            if not len(chid) > 2:
                await message.reply_text(
                    "Enter valid channel username"
                )
                return
    except Exception:
        await message.reply_text(
            "Enter a valid ID\n"
            "ID will be in <b>-100xxxxxxxxxx</b> format\n"
            "You can also use username of channel with @ symbol",
        )
        return

    try:
        invitelink = await client.export_chat_invite_link(chid)
    except:
        await message.reply_text(
            "<i>Add me as admin in your channel with admin rights - 'Invite Users via Link' and try again</i>",
        )
        return

    try:
        user = await client.USER.get_me()
    except:
        user.first_name =  " "

    try:
        await client.USER.join_chat(invitelink)
    except UserAlreadyParticipant:
        pass
    except Exception as e:
        print(e)
        await message.reply_text(
            f"<i>User {user.first_name} couldn't join your channel! Make sure user is not banned in channel."
            "\n\nOr manually add the user to your channel and try again</i>",
        )
        return

    try:
        chatdetails = await client.USER.get_chat(chid)
    except:
        await message.reply_text(
            "<i>Send a message to your channel and try again</i>"
        )
        return

    intmsg = await message.reply_text(
        "<i>Please wait while I'm adding your channel files to DB"
        "\n\nIt may take some time if you have more files in channel!!"
        "\nDon't give any other commands now!</i>"
    )

    channel_id = chatdetails.id
    channel_name = chatdetails.title
    group_id = message.chat.id
    group_name = message.chat.title

    already_added = await ifexists(channel_id, group_id)
    if already_added:
        await intmsg.edit_text("Channel already added to db!")
        return

    docs = []

    if DOC_SEARCH == "yes":
        try:
            async for msg in client.USER.search_messages(channel_id,filter='document'):
                try:
                    file_name = msg.document.file_name
                    file_id = msg.document.file_id
                    file_size = msg.document.file_size                   
                    link = msg.link
                    data = {
                        '_id': file_id,
                        'channel_id' : channel_id,
                        'file_name': file_name,
                        'file_size': file_size,
                        'link': link
                    }
                    docs.append(data)
                except:
                    pass
        except:
            pass

        await asyncio.sleep(5)

    if VID_SEARCH == "yes":
        try:
            async for msg in client.USER.search_messages(channel_id,filter='video'):
                try:
                    file_name = msg.video.file_name
                    file_id = msg.video.file_id   
                    file_size = msg.video.file_size              
                    link = msg.link
                    data = {
                        '_id': file_id,
                        'channel_id' : channel_id,
                        'file_name': file_name,
                        'file_size': file_size,
                        'link': link
                    }
                    docs.append(data)
                except:
                    pass
        except:
            pass

        await asyncio.sleep(5)

    if MUSIC_SEARCH == "yes":
        try:
            async for msg in client.USER.search_messages(channel_id,filter='audio'):
                try:
                    file_name = msg.audio.file_name
                    file_id = msg.audio.file_id   
                    file_size = msg.audio.file_size                 
                    link = msg.link
                    data = {
                        '_id': file_id,
                        'channel_id' : channel_id,
                        'file_name': file_name,
                        'file_size': file_size,
                        'link': link
                    }
                    docs.append(data)
                except:
                    pass
        except:
            pass

    if docs:
        await savefiles(docs, group_id)
    else:
        await intmsg.edit_text("Channel couldn't be added. Try after some time!")
        return

    await channelgroup(channel_id, channel_name, group_id, group_name)

    await intmsg.edit_text("Channel added successfully!")


@Client.on_message(filters.group & filters.command(["fdel"]))
async def deletechannelfilters(client, message: Message):

    if message.from_user.id not in AUTH_USERS:
        return

    try:
        cmd, text = message.text.split(" ", 1)
    except:
        await message.reply_text(
            "<i>Enter in correct format!\n\n<code>/del channelid</code>  or\n"
            "<code>/del @channelusername</code></i>"
            "\n\nrun /filterstats to see connected channels",
        )
        return
    try:
        if not text.startswith("@"):
            chid = int(text)
            if not len(text) == 14:
                await message.reply_text(
                    "Enter valid channel ID\n\nrun /filterstats to see connected channels"
                )
                return
        elif text.startswith("@"):
            chid = text
            if not len(chid) > 2:
                await message.reply_text(
                    "Enter valid channel username"
                )
                return
    except Exception:
        await message.reply_text(
            "Enter a valid ID\n"
            "run /filterstats to see connected channels\n"
            "You can also use username of channel with @ symbol",
        )
        return

    try:
        chatdetails = await client.USER.get_chat(chid)
    except:
        await message.reply_text(
            "<i>User must be present in given channel.\n\n"
            "If user is already present, send a message to your channel and try again</i>"
        )
        return

    intmsg = await message.reply_text(
        "<i>Please wait while I'm deleteing your channel"
        "\n\nDon't give any other commands now!</i>"
    )

    channel_id = chatdetails.id
    channel_name = chatdetails.title
    group_id = message.chat.id
    group_name = message.chat.title

    already_added = await ifexists(channel_id, group_id)
    if not already_added:
        await intmsg.edit_text("That channel is not currently added in db!")
        return

    delete_files = await deletefiles(channel_id, channel_name, group_id, group_name)
    
    if delete_files:
        await intmsg.edit_text(
            "Channel deleted successfully!"
        )
    else:
        await intmsg.edit_text(
            "Couldn't delete Channel"
        )


@Client.on_message(filters.group & filters.command(["fdelall"]))
async def delallconfirm(client, message: Message):
    await message.reply_text(
        "Are you sure?? This will disconnect all connected channels and deletes all filters in group",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(text="YES",callback_data="delallconfirm")],
            [InlineKeyboardButton(text="CANCEL",callback_data="delallcancel")]
        ])
    )


async def deleteallfilters(client, message: Message):

    if message.reply_to_message.from_user.id not in AUTH_USERS:
        return

    intmsg = await message.reply_to_message.reply_text(
        "<i>Please wait while I'm deleteing your channel.</i>"
        "\n\nDon't give any other commands now!</i>"
    )

    group_id = message.reply_to_message.chat.id

    await deletealldetails(group_id)

    delete_all = await deletegroupcol(group_id)

    if delete_all == 0:
        await intmsg.edit_text(
            "All filters from group deleted successfully!"
        )
    elif delete_all == 1:
        await intmsg.edit_text(
            "Nothing to delete!!"
        )
    elif delete_all == 2:
        await intmsg.edit_text(
            "Couldn't delete filters. Try again after sometime.."
        )  


@Client.on_message(filters.group & filters.command(["filterstats"]))
async def stats(client, message: Message):

    if message.from_user.id not in AUTH_USERS:
        return

    group_id = message.chat.id
    group_name = message.chat.title

    stats = f"Stats for Auto Filter Bot in {group_name}\n\n<b>Connected channels ;</b>"

    chdetails = await channeldetails(group_id)
    if chdetails:
        n = 0
        for eachdetail in chdetails:
            details = f"\n{n+1} : {eachdetail}"
            stats += details
            n = n + 1
    else:
        stats += "\nNo channels connected in current group!!"
        await message.reply_text(stats)
        return

    total = await countfilters(group_id)
    if total:
        stats += f"\n\n<b>Total number of filters</b> : {total}"

    await message.reply_text(stats)


@Client.on_message(filters.channel & (filters.document | filters.video | filters.audio))
async def addnewfiles(client, message: Message):

    media = message.document or message.video or message.audio

    channel_id = message.chat.id
    file_name = media.file_name
    file_size = media.file_size
    file_id = media.file_id
    link = message.link

    docs = []
    data = {
        '_id': file_id,
        'channel_id' : channel_id,
        'file_name': file_name,
        'file_size': file_size,
        'link': link
    }
    docs.append(data)

    groupids = await findgroupid(channel_id)
    if groupids:
        for group_id in groupids:
            await savefiles(docs, group_id)
