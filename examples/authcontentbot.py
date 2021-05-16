#!/usr/bin/env python
#
# Semaphore: A simple (rule-based) bot library for Signal Private Messenger.
# Copyright (C) 2021 Lazlo Westerhof <semaphore@lazlo.me>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
Signal Bot example, get reward by sending photo to IPFS or verify the photo.
"""
import json
import mimetypes
import logging
import os
from pathlib import Path

import anyio
import asks  # type: ignore
import feedparser  # type: ignore
import requests
from bs4 import BeautifulSoup  # type: ignore

from semaphore import Bot, ChatContext


# Filepath of the latest received photo
Latest_photo = ''

# IPFS URL of the latest received photo
Latest_photo_url = 'https://ipfs.io./ipfs/defaultcid'

# Verifier list. All the verifiers will get notifications to verify photos.
# The list contains verifiers' phone numbers.
Verifiers = []


def ipfs_add(filepath, cid_version=1):
    """ Add file to IPFS via infura API """

    mimetypes.init()
    mimetype = mimetypes.guess_type(filepath)[0]

    if cid_version == 1:
        url = "https://ipfs.infura.io:5001/api/v0/add?cid-version=1&raw-leaves=false"
    else:
        url = "https://ipfs.infura.io:5001/api/v0/add?&raw-leaves=false"
    payload = {}
    files = [
      ('file', (os.path.basename(filepath), open(filepath, 'rb'), mimetype))
    ]
    headers = {}
    response = requests.request(
        "POST", url, headers=headers, data=payload, files=files
    )
    ipfs_cid = json.loads(response.text)['Hash']
    return ipfs_cid


async def ipfs(ctx: ChatContext) -> None:
    global Latest_photo
    global Latest_photo_url
    global Verifiers

    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print("ctx.message: {}".format(ctx.message))
    print("data message: {}".format(ctx.message.data_message))
    print("message source number: {}".format(ctx.message.source.number))
    print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")

    if len(ctx.message.data_message.body) == 0 and len(ctx.message.data_message.attachments) > 0:
        # Case: The bot receives a photo
        for attachment in ctx.message.data_message.attachments:
            if attachment.content_type in ["image/png", "image/jpeg"]:
                print("Get PNG/JPEG stored at {}".format(attachment.stored_filename))
                Latest_photo = attachment.stored_filename
        # TODO: We only handle the latest photo currently.
        await ctx.message.reply(body="Do you want to archive the photo to IPFS? (y/n): ")
    elif len(ctx.message.data_message.body) > 0:
        # Case: The bot receives a message 

        # HACKING: /var/lib/signald/attachments/ permission
        # is 700 & signald:signald
        # change to 755

        cmd = ctx.message.data_message.body.split(' ')[0].lower()
        print('Command: ' + cmd)

        if len(Latest_photo) > 0:
            if ctx.message.data_message.body.lower() in ['y', 'yes']:
                cid = ipfs_add(Latest_photo)
                Latest_photo = ''
                Latest_photo_url = 'https://ipfs.io/ipfs/' + cid
                await ctx.message.reply(body="The photo has been archived to IPFS\n\nhttps://ipfs.io/ipfs/" + cid)

            elif ctx.message.data_message.body.lower() in ['n', 'no']:
                Latest_photo = ''
                await ctx.message.reply(body="I will not archive the uploaded photo to IPFS")
        elif cmd == '/register':
            Verifiers.append(ctx.message.source.number)
            await ctx.message.reply(body="{} is a verifier now".format(ctx.message.source.number))
        elif cmd == '/verify':
            # get latest photo URL to verify
            if ctx.message.source.number in Verifiers:
                msg = 'Do you agree the authenticity of the photo?\n\n{0}\n\nagree: /agree y\ndisagree: /agree n'.format(Latest_photo_url)
                await ctx.message.reply(body=msg)
            else:
                msg = 'You are not a verifier. Send "/register" to be a verifier'
                await ctx.message.reply(body=msg)
        elif cmd == '/agree':
            if ctx.message.source.number in Verifiers:
                agreement = ctx.message.data_message.body.split(' ')[1].lower()
                msg = 'Verification agreement by {0}: {1}'.format(ctx.message.source.number, agreement)
                await ctx.message.reply(body=msg)

                msg = 'Both you and the photo sender will get MOBs as rewards'
                await ctx.message.reply(body=msg)
            else:
                msg = 'You are not a verifier. Send "/register" to be a verifier'
                await ctx.message.reply(body=msg)
        else:
            # echo
            await ctx.message.reply(body=ctx.message.data_message.body)
    else:
        print("Receive unknown message whose body and attachment are empty.")


async def main():
    """Start the bot."""
    # Connect the bot to number.
    async with Bot(os.environ["SIGNAL_PHONE_NUMBER"]) as bot:
        bot.register_handler("", ipfs)

        # Run the bot until you press Ctrl-C.
        await bot.start()


if __name__ == '__main__':
    anyio.run(main)
