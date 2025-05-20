# yourapp/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class VideoChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'room_{self.room_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        self.peer_id = self.channel_name  # Use channel_name as unique peerID

        # Notify existing peers
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'add.peer',
                'peerID': self.peer_id,
                'createOffer': False,
                'sender': self.peer_id
            }
        )

        # Notify joining peer of existing peers
        for peer_channel in self.channel_layer.groups[self.room_group_name]:
            if peer_channel != self.peer_id:
                await self.send(text_data=json.dumps({
                    'action': 'add-peer',
                    'peerID': peer_channel,
                    'createOffer': True
                }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Notify others to remove peer
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'remove.peer',
                'peerID': self.peer_id,
            }
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        peerID = data.get('peerID')

        if action == 'relay-sdp':
            await self.channel_layer.send(peerID, {
                'type': 'session.description',
                'peerID': self.peer_id,
                'sessionDescription': data['sessionDescription']
            })

        elif action == 'relay-ice':
            await self.channel_layer.send(peerID, {
                'type': 'ice.candidate',
                'peerID': self.peer_id,
                'iceCandidate': data['iceCandidate']
            })

    # Event methods
    async def add_peer(self, event):
        if event['sender'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'action': 'add-peer',
                'peerID': event['peerID'],
                'createOffer': event['createOffer']
            }))

    async def session_description(self, event):
        await self.send(text_data=json.dumps({
            'action': 'session-description',
            'peerID': event['peerID'],
            'sessionDescription': event['sessionDescription']
        }))

    async def ice_candidate(self, event):
        await self.send(text_data=json.dumps({
            'action': 'ice-candidate',
            'peerID': event['peerID'],
            'iceCandidate': event['iceCandidate']
        }))

    async def remove_peer(self, event):
        await self.send(text_data=json.dumps({
            'action': 'remove-peer',
            'peerID': event['peerID']
        }))
