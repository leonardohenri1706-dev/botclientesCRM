import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { createServer } from 'http';
import { Server } from 'socket.io';
import { Queue, Worker } from 'bullmq';
import IORedis from 'ioredis';
import axios from 'axios';
import qrcode from 'qrcode-terminal';

dotenv.config();

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: { origin: '*' }
});

app.use(cors());
app.use(express.json());

const redis = new IORedis(process.env.REDIS_URL || 'redis://localhost:6379');

// BullMQ queues
const outreachQueue = new Queue('outreach', { connection: redis });
const webhookQueue = new Queue('webhooks', { connection: redis });

// Evolution API config
const EVOLUTION_API_URL = process.env.EVOLUTION_API_URL;
const EVOLUTION_API_KEY = process.env.EVOLUTION_API_KEY;
const EVOLUTION_INSTANCE = process.env.EVOLUTION_INSTANCE_NAME;
const PORT = process.env.PORT || 3001;

const evolutionHeaders = {
  'apikey': EVOLUTION_API_KEY,
  'Content-Type': 'application/json'
};

// Socket.io for real-time updates to frontend
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
  
  socket.on('join-campaign', (campaignId) => {
    socket.join(`campaign-${campaignId}`);
    console.log(`Client ${socket.id} joined campaign ${campaignId}`);
  });
  
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Broadcast to campaign room
function broadcastToCampaign(campaignId, event, data) {
  io.to(`campaign-${campaignId}`).emit(event, data);
}

// Evolution API helpers
async function evolutionRequest(endpoint, method = 'GET', data = null) {
  const url = `${EVOLUTION_API_URL}${endpoint}`;
  try {
    const response = await axios({ method, url, data, headers: evolutionHeaders });
    return response.data;
  } catch (error) {
    console.error(`Evolution API Error [${endpoint}]:`, error.response?.data || error.message);
    throw error;
  }
}

// Webhook endpoint for Evolution API
app.post('/webhook/evolution', async (req, res) => {
  try {
    const { event, data, instance } = req.body;
    console.log(`Webhook received: ${event} for instance ${instance}`);
    
    // Add to webhook queue for processing
    await webhookQueue.add('process-webhook', { event, data, instance });
    
    res.status(200).json({ received: true });
  } catch (error) {
    console.error('Webhook error:', error);
    res.status(500).json({ error: 'Webhook processing failed' });
  }
});

// Process webhook worker
const webhookWorker = new Worker('webhooks', async (job) => {
  const { event, data, instance } = job.data;
  
  switch (event) {
    case 'messages.upsert':
      await handleIncomingMessage(data);
      break;
    case 'connection.update':
      await handleConnectionUpdate(data);
      break;
    case 'qrcode.updated':
      await handleQRCodeUpdate(data);
      break;
    case 'presence.update':
      await handlePresenceUpdate(data);
      break;
    default:
      console.log(`Unhandled webhook event: ${event}`);
  }
}, { connection: redis });

async function handleIncomingMessage(data) {
  const messages = data.messages || [data];
  
  for (const msg of messages) {
    if (msg.fromMe) continue; // Skip own messages
    
    const phoneNumber = msg.key.remoteJid?.replace('@s.whatsapp.net', '');
    const messageText = msg.message?.conversation || 
                       msg.message?.extendedTextMessage?.text ||
                       msg.message?.audioMessage ? '[Áudio]' : 
                       '[Mídia]';
    
    console.log(`Incoming from ${phoneNumber}: ${messageText}`);
    
    // Broadcast to frontend
    broadcastToCampaign('all', 'new-message', {
      phoneNumber,
      message: messageText,
      timestamp: msg.messageTimestamp,
      messageId: msg.key.id
    });
    
    // TODO: Process with LLM and queue response
  }
}

async function handleConnectionUpdate(data) {
  const { state, statusReason } = data;
  console.log(`Connection state: ${state}`, statusReason ? `- ${statusReason}` : '');
  
  broadcastToCampaign('all', 'connection-update', { state, statusReason });
  
  if (state === 'close' && statusReason === 'logout') {
    // Instance disconnected, need to reconnect
    console.log('Instance logged out, attempting reconnect...');
    setTimeout(() => connectInstance(), 5000);
  }
}

async function handleQRCodeUpdate(data) {
  if (data.qrcode) {
    console.log('QR Code updated - scan with WhatsApp:');
    qrcode.generate(data.qrcode, { small: true });
    
    broadcastToCampaign('all', 'qrcode-update', { qrcode: data.qrcode });
  }
}

async function handlePresenceUpdate(data) {
  const { presence, number } = data;
  console.log(`Presence update: ${number} - ${presence}`);
  
  broadcastToCampaign('all', 'presence-update', { number, presence });
}

// Instance management
async function connectInstance() {
  try {
    await evolutionRequest(`/instance/connect/${EVOLUTION_INSTANCE}`, 'GET');
    console.log('Instance connection initiated');
  } catch (error) {
    console.error('Failed to connect instance:', error.message);
  }
}

async function createInstance() {
  try {
    await evolutionRequest(`/instance/create`, 'POST', {
      instanceName: EVOLUTION_INSTANCE,
      token: EVOLUTION_API_KEY,
      qrcode: true,
      integration: 'WHATSAPP-BAILEYS'
    });
    console.log('Instance created');
  } catch (error) {
    if (error.response?.status !== 409) { // 409 = already exists
      throw error;
    }
    console.log('Instance already exists');
  }
}

// API Routes
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'botclientes-node-services' });
});

// Get instance status
app.get('/api/instance/status', async (req, res) => {
  try {
    const data = await evolutionRequest(`/instance/connectionState/${EVOLUTION_INSTANCE}`);
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get QR Code
app.get('/api/instance/qrcode', async (req, res) => {
  try {
    const data = await evolutionRequest(`/instance/qrcode/${EVOLUTION_INSTANCE}`);
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Send text message
app.post('/api/messages/send-text', async (req, res) => {
  try {
    const { number, text } = req.body;
    const data = await evolutionRequest(`/message/sendText/${EVOLUTION_INSTANCE}`, 'POST', {
      number,
      text
    });
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Send audio message
app.post('/api/messages/send-audio', async (req, res) => {
  try {
    const { number, audio, ptt = true } = req.body;
    const data = await evolutionRequest(`/message/sendWhatsAppAudio/${EVOLUTION_INSTANCE}`, 'POST', {
      number,
      audio,
      ptt
    });
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Send presence
app.post('/api/chat/send-presence', async (req, res) => {
  try {
    const { number, presence, delay } = req.body;
    const data = await evolutionRequest(`/chat/sendPresence/${EVOLUTION_INSTANCE}`, 'POST', {
      number,
      presence,
      delay
    });
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get contacts
app.get('/api/contacts', async (req, res) => {
  try {
    const data = await evolutionRequest(`/chat/findContacts/${EVOLUTION_INSTANCE}`);
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get chats
app.get('/api/chats', async (req, res) => {
  try {
    const data = await evolutionRequest(`/chat/findChats/${EVOLUTION_INSTANCE}`);
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Outreach queue worker (for processing outreach jobs from Python backend)
const outreachWorker = new Worker('outreach', async (job) => {
  const { leadId, phoneNumber, textMessage, audioPath, leadContext } = job.data;
  
  try {
    // Simulate typing
    await evolutionRequest(`/chat/sendPresence/${EVOLUTION_INSTANCE}`, 'POST', {
      number: phoneNumber,
      presence: 'composing',
      delay: Math.floor(Math.random() * 2000) + 4000
    });
    
    await new Promise(r => setTimeout(r, Math.random() * 2000 + 4000));
    
    // Send text
    await evolutionRequest(`/message/sendText/${EVOLUTION_INSTANCE}`, 'POST', {
      number: phoneNumber,
      text: textMessage
    });
    
    // Send audio if provided
    if (audioPath) {
      await evolutionRequest(`/chat/sendPresence/${EVOLUTION_INSTANCE}`, 'POST', {
        number: phoneNumber,
        presence: 'recording',
        delay: Math.floor(Math.random() * 3000) + 5000
      });
      
      await new Promise(r => setTimeout(r, Math.random() * 3000 + 5000));
      
      await evolutionRequest(`/message/sendWhatsAppAudio/${EVOLUTION_INSTANCE}`, 'POST', {
        number: phoneNumber,
        audio: audioPath,
        ptt: true
      });
    }
    
    // Broadcast completion
    broadcastToCampaign(leadContext.campaignId || 'all', 'outreach-complete', {
      leadId,
      status: 'sent',
      hasAudio: !!audioPath
    });
    
    return { success: true };
  } catch (error) {
    console.error(`Outreach failed for lead ${leadId}:`, error);
    throw error;
  }
}, { connection: redis, concurrency: 1 });

// Initialize
async function initialize() {
  await createInstance();
  await connectInstance();
  
  httpServer.listen(PORT, () => {
    console.log(`Node services running on port ${PORT}`);
    console.log(`Webhook endpoint: http://localhost:${PORT}/webhook/evolution`);
    console.log(`Socket.io ready for real-time updates`);
  });
}

initialize().catch(console.error);

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('Shutting down...');
  await outreachWorker.close();
  await webhookWorker.close();
  await redis.quit();
  httpServer.close();
  process.exit(0);
});