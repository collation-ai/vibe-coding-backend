#!/usr/bin/env node

/**
 * Complete Authentication Gateway Test Suite
 * Tests login, session management, proxy requests, and logout
 */

const https = require('https');
const readline = require('readline');

// Configuration
const GATEWAY_HOST = 'vibe-auth-gateway.azurewebsites.net';
const BACKEND_PATH = '/api/databases'; // Example endpoint to test

// Store session data
let sessionCookie = null;
let csrfToken = null;

// Colors for output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

// Helper function to make HTTPS requests
function makeRequest(options, data = null) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let responseData = '';

      res.on('data', (chunk) => {
        responseData += chunk;
      });

      res.on('end', () => {
        resolve({
          status: res.statusCode,
          headers: res.headers,
          body: responseData
        });
      });
    });

    req.on('error', reject);

    if (data) {
      req.write(typeof data === 'string' ? data : JSON.stringify(data));
    }
    
    req.end();
  });
}

// Test 1: Login
async function testLogin(username, password) {
  log('\n📝 Test 1: Login', 'blue');
  log(`Testing login for user: ${username}`);

  const response = await makeRequest({
    hostname: GATEWAY_HOST,
    path: '/api/auth/login',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  }, { username, password });

  log(`Response Status: ${response.status}`);

  if (response.status === 200) {
    const data = JSON.parse(response.body);
    
    // Extract session cookie
    const setCookieHeader = response.headers['set-cookie'];
    if (setCookieHeader && setCookieHeader[0]) {
      sessionCookie = setCookieHeader[0].split(';')[0];
      log(`✅ Session Cookie: ${sessionCookie}`, 'green');
    }

    // Extract CSRF token
    if (data.data && data.data.csrfToken) {
      csrfToken = data.data.csrfToken;
      log(`✅ CSRF Token: ${csrfToken}`, 'green');
      log(`✅ Username: ${data.data.username}`, 'green');
      log(`✅ Email: ${data.data.email}`, 'green');
      log(`✅ Session expires in: ${data.data.expiresIn} seconds`, 'green');
    }

    return true;
  } else {
    log(`❌ Login failed: ${response.body}`, 'red');
    return false;
  }
}

// Test 2: Make Proxy Request
async function testProxyRequest() {
  log('\n🔄 Test 2: Proxy Request', 'blue');
  
  if (!sessionCookie || !csrfToken) {
    log('❌ No session or CSRF token available', 'red');
    return false;
  }

  log(`Making proxy request to: ${BACKEND_PATH}`);

  const response = await makeRequest({
    hostname: GATEWAY_HOST,
    path: `/api/proxy${BACKEND_PATH}`,
    method: 'GET',
    headers: {
      'Cookie': sessionCookie,
      'X-CSRF-Token': csrfToken,
      'Content-Type': 'application/json'
    }
  });

  log(`Response Status: ${response.status}`);

  if (response.status === 200) {
    log('✅ Proxy request successful', 'green');
    try {
      const data = JSON.parse(response.body);
      log(`Response data: ${JSON.stringify(data, null, 2).substring(0, 200)}...`, 'green');
    } catch (e) {
      log(`Response: ${response.body.substring(0, 200)}...`, 'green');
    }
    return true;
  } else {
    log(`❌ Proxy request failed: ${response.body}`, 'red');
    return false;
  }
}

// Test 3: Invalid Session
async function testInvalidSession() {
  log('\n🚫 Test 3: Invalid Session', 'blue');
  log('Testing proxy request with invalid session...');

  const response = await makeRequest({
    hostname: GATEWAY_HOST,
    path: `/api/proxy${BACKEND_PATH}`,
    method: 'GET',
    headers: {
      'Cookie': 'vibe_session=invalid-session-id',
      'X-CSRF-Token': 'invalid-csrf-token',
      'Content-Type': 'application/json'
    }
  });

  log(`Response Status: ${response.status}`);

  if (response.status === 401 || response.status === 403) {
    log('✅ Invalid session correctly rejected', 'green');
    return true;
  } else {
    log(`❌ Expected 401/403 but got ${response.status}`, 'red');
    return false;
  }
}

// Test 4: Logout
async function testLogout() {
  log('\n🚪 Test 4: Logout', 'blue');
  
  if (!sessionCookie || !csrfToken) {
    log('❌ No session or CSRF token available', 'red');
    return false;
  }

  const response = await makeRequest({
    hostname: GATEWAY_HOST,
    path: '/api/auth/logout',
    method: 'POST',
    headers: {
      'Cookie': sessionCookie,
      'X-CSRF-Token': csrfToken,
      'Content-Type': 'application/json'
    }
  });

  log(`Response Status: ${response.status}`);

  if (response.status === 200) {
    log('✅ Logout successful', 'green');
    sessionCookie = null;
    csrfToken = null;
    return true;
  } else {
    log(`❌ Logout failed: ${response.body}`, 'red');
    return false;
  }
}

// Test 5: Verify Session Invalidated
async function testSessionInvalidated() {
  log('\n🔒 Test 5: Verify Session Invalidated', 'blue');
  log('Testing that the old session is no longer valid...');

  const response = await makeRequest({
    hostname: GATEWAY_HOST,
    path: `/api/proxy${BACKEND_PATH}`,
    method: 'GET',
    headers: {
      'Cookie': sessionCookie || 'vibe_session=logged-out',
      'X-CSRF-Token': csrfToken || 'logged-out',
      'Content-Type': 'application/json'
    }
  });

  log(`Response Status: ${response.status}`);

  if (response.status === 401 || response.status === 403) {
    log('✅ Session correctly invalidated after logout', 'green');
    return true;
  } else {
    log(`❌ Expected 401/403 but got ${response.status}`, 'red');
    return false;
  }
}

// Interactive test runner
async function runInteractiveTests() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  const question = (query) => new Promise((resolve) => {
    rl.question(query, resolve);
  });

  log('\n🧪 Vibe Auth Gateway Test Suite', 'yellow');
  log('=' .repeat(50));
  
  const username = await question('Enter username (default: tanmais): ') || 'tanmais';
  const password = await question('Enter password (default: Login123#): ') || 'Login123#';
  
  rl.close();

  log('\n' + '='.repeat(50));
  log('Starting tests...', 'yellow');

  const results = [];

  // Run tests
  results.push(await testLogin(username, password));
  
  if (results[0]) {
    results.push(await testProxyRequest());
    results.push(await testInvalidSession());
    results.push(await testLogout());
    results.push(await testSessionInvalidated());
  }

  // Summary
  log('\n' + '='.repeat(50));
  log('📊 Test Summary', 'yellow');
  log('=' .repeat(50));
  
  const passed = results.filter(r => r === true).length;
  const total = results.length;
  
  if (passed === total) {
    log(`✅ All ${total} tests passed!`, 'green');
  } else {
    log(`⚠️  ${passed}/${total} tests passed`, 'yellow');
  }
}

// Quick test runner (non-interactive)
async function runQuickTests() {
  log('\n🚀 Quick Test Suite', 'yellow');
  log('=' .repeat(50));
  log('Using default credentials: tanmais / Login123#');

  const results = [];

  // Run all tests with default credentials
  results.push(await testLogin('tanmais', 'Login123#'));
  
  if (results[0]) {
    results.push(await testProxyRequest());
    results.push(await testInvalidSession());
    results.push(await testLogout());
    results.push(await testSessionInvalidated());
  }

  // Summary
  log('\n' + '='.repeat(50));
  log('📊 Test Summary', 'yellow');
  log('=' .repeat(50));
  
  const passed = results.filter(r => r === true).length;
  const total = results.length;
  
  if (passed === total) {
    log(`✅ All ${total} tests passed!`, 'green');
  } else {
    log(`⚠️  ${passed}/${total} tests passed`, 'yellow');
  }

  return passed === total ? 0 : 1;
}

// Main execution
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.includes('--quick') || args.includes('-q')) {
    runQuickTests().then(exitCode => process.exit(exitCode));
  } else {
    runInteractiveTests().then(() => process.exit(0));
  }
}

module.exports = { testLogin, testProxyRequest, testLogout };