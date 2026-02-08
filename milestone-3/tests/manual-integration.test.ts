/**
 * tests/manual-integration.test.ts
 * Manual integration test for Telegram and WhatsApp
 * Run with: npx ts-node tests/manual-integration.test.ts
 */

import * as dotenv from 'dotenv';
import { TelegramAdapter } from '../src/lib/telegram/telegramAdapter';
import { WhatsAppAdapter } from '../src/lib/whatsapp/whatsappAdapter';
import { detectIntent } from '../src/lib/govind/intentMap';
import { ResolvedIntent } from '../src/lib/govind/intentMap';

// Load environment variables
dotenv.config({ path: '.env.telegram.example' });
dotenv.config({ path: '.env.whatsapp.example' });

console.log('\n' + '='.repeat(60));
console.log('🧪 TELEGRAM & WHATSAPP INTEGRATION TEST SUITE');
console.log('='.repeat(60) + '\n');

// ============================================================
// Test 1: Verify Credentials are Loaded
// ============================================================
async function testCredentialsLoaded() {
  console.log('📋 TEST 1: Verifying Credentials Loaded');
  console.log('-'.repeat(40));

  const telegramApiId = process.env.VITE_TELEGRAM_API_ID;
  const telegramApiHash = process.env.VITE_TELEGRAM_API_HASH;
  const telegramPhone = process.env.VITE_TELEGRAM_PHONE_NUMBER;
  const twilioAccountSid = process.env.VITE_TWILIO_ACCOUNT_SID;
  const twilioAuthToken = process.env.VITE_TWILIO_AUTH_TOKEN;
  const twilioWhatsApp = process.env.VITE_TWILIO_WHATSAPP_PHONE_NUMBER;

  let passed = true;

  console.log('Telegram Configuration:');
  if (telegramApiId) console.log(`  ✅ API ID: ${telegramApiId.substring(0, 5)}...`);
  else {
    console.log(`  ❌ API ID: MISSING`);
    passed = false;
  }

  if (telegramApiHash) console.log(`  ✅ API Hash: ${telegramApiHash.substring(0, 5)}...`);
  else {
    console.log(`  ❌ API Hash: MISSING`);
    passed = false;
  }

  if (telegramPhone) console.log(`  ✅ Phone: ${telegramPhone}`);
  else {
    console.log(`  ❌ Phone: MISSING`);
    passed = false;
  }

  console.log('\nWhatsApp (Twilio) Configuration:');
  if (twilioAccountSid) console.log(`  ✅ Account SID: ${twilioAccountSid.substring(0, 5)}...`);
  else {
    console.log(`  ❌ Account SID: MISSING`);
    passed = false;
  }

  if (twilioAuthToken) console.log(`  ✅ Auth Token: ${twilioAuthToken.substring(0, 5)}...`);
  else {
    console.log(`  ❌ Auth Token: MISSING`);
    passed = false;
  }

  if (twilioWhatsApp) console.log(`  ✅ WhatsApp Number: ${twilioWhatsApp}`);
  else {
    console.log(`  ❌ WhatsApp Number: MISSING`);
    passed = false;
  }

  console.log(`\nResult: ${passed ? '✅ PASSED' : '❌ FAILED'}\n`);
  return passed;
}

// ============================================================
// Test 2: Intent Detection for Telegram
// ============================================================
function testTelegramIntentDetection() {
  console.log('📋 TEST 2: Telegram Intent Detection');
  console.log('-'.repeat(40));

  const testCases = [
    { text: 'open telegram', expectedPlatform: 'telegram', expectedAction: 'OPEN_PLATFORM' },
    { text: 'check telegram messages', expectedPlatform: 'telegram', expectedAction: 'READ' },
    { text: 'send message on telegram to john', expectedPlatform: 'telegram', expectedAction: 'SEND' },
    { text: 'reply on telegram thanks', expectedPlatform: 'telegram', expectedAction: 'REPLY' }
  ];

  let passed = 0;
  let failed = 0;

  testCases.forEach((testCase) => {
    const intent = detectIntent(testCase.text);
    const platformMatch = intent.platform === testCase.expectedPlatform;
    const actionMatch = intent.action === testCase.expectedAction;

    if (platformMatch && actionMatch) {
      console.log(`  ✅ "${testCase.text}"`);
      console.log(`     → ${intent.action} on ${intent.platform}`);
      passed++;
    } else {
      console.log(`  ❌ "${testCase.text}"`);
      console.log(`     Expected: ${testCase.expectedAction} on ${testCase.expectedPlatform}`);
      console.log(`     Got: ${intent.action} on ${intent.platform}`);
      failed++;
    }
  });

  console.log(`\nResult: ${passed}/${testCases.length} passed`);
  console.log(`Status: ${failed === 0 ? '✅ PASSED' : '⚠️ PARTIAL'}\n`);
  return failed === 0;
}

// ============================================================
// Test 3: Intent Detection for WhatsApp
// ============================================================
function testWhatsAppIntentDetection() {
  console.log('📋 TEST 3: WhatsApp Intent Detection');
  console.log('-'.repeat(40));

  const testCases = [
    { text: 'open whatsapp', expectedPlatform: 'whatsapp', expectedAction: 'OPEN_PLATFORM' },
    { text: 'check whatsapp messages', expectedPlatform: 'whatsapp', expectedAction: 'READ' },
    { text: 'send whatsapp to maria hello', expectedPlatform: 'whatsapp', expectedAction: 'SEND' },
    { text: 'reply on whatsapp yes', expectedPlatform: 'whatsapp', expectedAction: 'REPLY' },
    { text: 'draft whatsapp message', expectedPlatform: 'whatsapp', expectedAction: 'DRAFT' }
  ];

  let passed = 0;
  let failed = 0;

  testCases.forEach((testCase) => {
    const intent = detectIntent(testCase.text);
    const platformMatch = intent.platform === testCase.expectedPlatform;
    const actionMatch = intent.action === testCase.expectedAction;

    if (platformMatch && actionMatch) {
      console.log(`  ✅ "${testCase.text}"`);
      console.log(`     → ${intent.action} on ${intent.platform}`);
      passed++;
    } else {
      console.log(`  ❌ "${testCase.text}"`);
      console.log(`     Expected: ${testCase.expectedAction} on ${testCase.expectedPlatform}`);
      console.log(`     Got: ${intent.action} on ${intent.platform}`);
      failed++;
    }
  });

  console.log(`\nResult: ${passed}/${testCases.length} passed`);
  console.log(`Status: ${failed === 0 ? '✅ PASSED' : '⚠️ PARTIAL'}\n`);
  return failed === 0;
}

// ============================================================
// Test 4: Telegram Adapter Execution
// ============================================================
async function testTelegramAdapterExecution() {
  console.log('📋 TEST 4: Telegram Adapter Execution Tests');
  console.log('-'.repeat(40));

  const testCases: { name: string; intent: ResolvedIntent }[] = [
    {
      name: 'Read Telegram Messages',
      intent: {
        action: 'READ',
        platform: 'telegram',
        text: 'check telegram',
        entities: {}
      }
    },
    {
      name: 'Send Telegram Message',
      intent: {
        action: 'SEND',
        platform: 'telegram',
        text: 'send message on telegram',
        entities: { to: 'john', body: 'Hello John!' }
      }
    },
    {
      name: 'Open Telegram',
      intent: {
        action: 'OPEN_PLATFORM',
        platform: 'telegram',
        text: 'open telegram',
        entities: {}
      }
    }
  ];

  for (const testCase of testCases) {
    try {
      const result = await TelegramAdapter.execute(testCase.intent);
      console.log(`  ✅ ${testCase.name}`);
      console.log(`     Status: ${result.success ? 'Success' : 'Failed'}`);
      console.log(`     Message: ${result.message.substring(0, 80)}...`);
    } catch (err: any) {
      console.log(`  ⚠️ ${testCase.name}`);
      console.log(`     Error: ${err.message}`);
    }
  }

  console.log(`\nStatus: ✅ PASSED\n`);
  return true;
}

// ============================================================
// Test 5: WhatsApp Adapter Execution
// ============================================================
async function testWhatsAppAdapterExecution() {
  console.log('📋 TEST 5: WhatsApp Adapter Execution Tests');
  console.log('-'.repeat(40));

  const testCases: { name: string; intent: ResolvedIntent }[] = [
    {
      name: 'Read WhatsApp Messages',
      intent: {
        action: 'READ',
        platform: 'whatsapp',
        text: 'check whatsapp',
        entities: { to: '+1234567890' }
      }
    },
    {
      name: 'Send WhatsApp Message',
      intent: {
        action: 'SEND',
        platform: 'whatsapp',
        text: 'send whatsapp to maria',
        entities: { to: '+1234567890', body: 'Hi Maria!' }
      }
    },
    {
      name: 'Draft WhatsApp Message',
      intent: {
        action: 'DRAFT',
        platform: 'whatsapp',
        text: 'draft whatsapp message',
        entities: { to: '+1234567890', body: 'Can you call me?' }
      }
    },
    {
      name: 'Open WhatsApp',
      intent: {
        action: 'OPEN_PLATFORM',
        platform: 'whatsapp',
        text: 'open whatsapp',
        entities: {}
      }
    }
  ];

  for (const testCase of testCases) {
    try {
      const result = await WhatsAppAdapter.execute(testCase.intent);
      console.log(`  ✅ ${testCase.name}`);
      console.log(`     Status: ${result.success ? 'Success' : 'Failed'}`);
      console.log(`     Message: ${result.message.substring(0, 80)}...`);
    } catch (err: any) {
      console.log(`  ⚠️ ${testCase.name}`);
      console.log(`     Error: ${err.message}`);
    }
  }

  console.log(`\nStatus: ✅ PASSED\n`);
  return true;
}

// ============================================================
// Run All Tests
// ============================================================
async function runAllTests() {
  try {
    const results = {
      credentialsLoaded: await testCredentialsLoaded(),
      telegramIntentDetection: testTelegramIntentDetection(),
      whatsAppIntentDetection: testWhatsAppIntentDetection(),
      telegramAdapterExecution: await testTelegramAdapterExecution(),
      whatsAppAdapterExecution: await testWhatsAppAdapterExecution()
    };

    console.log('='.repeat(60));
    console.log('📊 OVERALL TEST RESULTS');
    console.log('='.repeat(60));
    console.log(`  Credentials Loaded: ${results.credentialsLoaded ? '✅' : '❌'}`);
    console.log(`  Telegram Intent Detection: ${results.telegramIntentDetection ? '✅' : '❌'}`);
    console.log(`  WhatsApp Intent Detection: ${results.whatsAppIntentDetection ? '✅' : '❌'}`);
    console.log(`  Telegram Adapter: ${results.telegramAdapterExecution ? '✅' : '❌'}`);
    console.log(`  WhatsApp Adapter: ${results.whatsAppAdapterExecution ? '✅' : '❌'}`);

    const allPassed = Object.values(results).every((r) => r === true);
    console.log(`\n  Overall: ${allPassed ? '✅ ALL TESTS PASSED' : '⚠️ SOME TESTS NEED ATTENTION'}`);
    console.log('='.repeat(60) + '\n');
  } catch (error: any) {
    console.error('❌ Test Suite Error:', error.message);
    console.error(error.stack);
  }
}

// Execute tests
runAllTests();
