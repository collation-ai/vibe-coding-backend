#!/usr/bin/env node

/**
 * Local Terminal Test for Authentication Gateway
 * Tests the deployed Azure Functions directly from your terminal
 */

const https = require('https');
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

async function makeRequest(options, data = null) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let responseData = '';
      res.on('data', (chunk) => responseData += chunk);
      res.on('end', () => {
        resolve({
          status: res.statusCode,
          headers: res.headers,
          body: responseData
        });
      });
    });
    req.on('error', reject);
    if (data) req.write(JSON.stringify(data));
    req.end();
  });
}

async function runTest() {
  log('\n=== Testing Authentication Gateway Locally ===\n', 'yellow');
  
  // Step 1: Login
  log('Step 1: Login to get session and CSRF token', 'blue');
  log('POST https://vibe-auth-gateway.azurewebsites.net/api/auth/login\n');
  
  const loginResponse = await makeRequest({
    hostname: 'vibe-auth-gateway.azurewebsites.net',
    path: '/api/auth/login',
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  }, {
    username: 'tanmais',
    password: 'Login123#'
  });
  
  // Extract session and CSRF
  const sessionCookie = loginResponse.headers['set-cookie'] ? 
    loginResponse.headers['set-cookie'][0].split(';')[0] : null;
  const loginData = JSON.parse(loginResponse.body);
  const csrfToken = loginData.data ? loginData.data.csrfToken : null;
  
  if (loginResponse.status === 200) {
    log('✅ Login successful!', 'green');
    log(`Session: ${sessionCookie}`, 'green');
    log(`CSRF Token: ${csrfToken}`, 'green');
    log(`Username: ${loginData.data.username}`, 'green');
    log(`Email: ${loginData.data.email}\n`, 'green');
  } else {
    log('❌ Login failed!', 'red');
    log(loginResponse.body, 'red');
    return;
  }
  
  // Step 2: Test Health Endpoint
  log('Step 2: Test health endpoint through proxy', 'blue');
  log('GET https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/health\n');
  
  const healthResponse = await makeRequest({
    hostname: 'vibe-auth-gateway.azurewebsites.net',
    path: '/api/proxy/api/health',
    method: 'GET',
    headers: {
      'Cookie': sessionCookie,
      'X-CSRF-Token': csrfToken,
      'Content-Type': 'application/json'
    }
  });
  
  if (healthResponse.status === 200) {
    log('✅ Health check successful!', 'green');
    const healthData = JSON.parse(healthResponse.body);
    log(JSON.stringify(healthData, null, 2), 'green');
  } else {
    log(`❌ Health check failed (Status: ${healthResponse.status})`, 'red');
    log(healthResponse.body, 'red');
  }
  
  // Step 3: Test Query Endpoint
  log('\nStep 3: Test query endpoint', 'blue');
  log('POST https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/query\n');
  
  const queryResponse = await makeRequest({
    hostname: 'vibe-auth-gateway.azurewebsites.net',
    path: '/api/proxy/api/query',
    method: 'POST',
    headers: {
      'Cookie': sessionCookie,
      'X-CSRF-Token': csrfToken,
      'Content-Type': 'application/json'
    }
  }, {
    database: 'master_db',
    query: 'SELECT version() as postgres_version',
    params: []
  });
  
  if (queryResponse.status === 200) {
    log('✅ Query successful!', 'green');
    const queryData = JSON.parse(queryResponse.body);
    log(JSON.stringify(queryData, null, 2), 'green');
  } else {
    log(`❌ Query failed (Status: ${queryResponse.status})`, 'red');
    log(queryResponse.body, 'red');
  }
  
  // Step 4: Logout
  log('\nStep 4: Logout', 'blue');
  log('POST https://vibe-auth-gateway.azurewebsites.net/api/auth/logout\n');
  
  const logoutResponse = await makeRequest({
    hostname: 'vibe-auth-gateway.azurewebsites.net',
    path: '/api/auth/logout',
    method: 'POST',
    headers: {
      'Cookie': sessionCookie,
      'X-CSRF-Token': csrfToken,
      'Content-Type': 'application/json'
    }
  });
  
  if (logoutResponse.status === 200) {
    log('✅ Logout successful!', 'green');
  } else {
    log('❌ Logout failed!', 'red');
    log(logoutResponse.body, 'red');
  }
  
  // Summary
  log('\n=== Test Complete ===', 'yellow');
  log('\nTo use in your application:', 'blue');
  log('1. Login to get session cookie and CSRF token');
  log('2. Include both in all API requests through /api/proxy/*');
  log('3. The gateway handles authentication with the real API key\n');
}

// Run the test
runTest().catch(console.error);