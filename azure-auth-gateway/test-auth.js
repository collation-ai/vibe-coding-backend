const fetch = require('node-fetch');
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

function prompt(question) {
    return new Promise(resolve => {
        rl.question(question, resolve);
    });
}

class AuthTester {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.sessionCookie = null;
        this.csrfToken = null;
    }

    async testLogin(username, password) {
        console.log('\n📝 Testing Login...');
        
        try {
            const response = await fetch(`${this.baseUrl}/api/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            const cookies = response.headers.raw()['set-cookie'];
            if (cookies) {
                // Extract session cookie
                const sessionCookie = cookies.find(c => c.includes('vibe_session'));
                if (sessionCookie) {
                    this.sessionCookie = sessionCookie.split(';')[0];
                    console.log('✅ Session cookie received');
                }
            }

            const data = await response.json();
            
            if (response.ok && data.success) {
                this.csrfToken = data.data.csrfToken;
                console.log('✅ Login successful');
                console.log(`   Username: ${data.data.username}`);
                console.log(`   Email: ${data.data.email}`);
                console.log(`   CSRF Token: ${this.csrfToken}`);
                console.log(`   Expires in: ${data.data.expiresIn} seconds`);
                return true;
            } else {
                console.log('❌ Login failed:', data.error);
                return false;
            }
        } catch (error) {
            console.log('❌ Login error:', error.message);
            return false;
        }
    }

    async testProxy() {
        console.log('\n📝 Testing Proxy (Health Check)...');
        
        if (!this.sessionCookie || !this.csrfToken) {
            console.log('❌ Not authenticated. Please login first.');
            return false;
        }

        try {
            const response = await fetch(`${this.baseUrl}/api/proxy/health`, {
                method: 'GET',
                headers: {
                    'X-CSRF-Token': this.csrfToken,
                    'Cookie': this.sessionCookie
                }
            });

            const data = await response.json();
            
            if (response.ok) {
                console.log('✅ Proxy working');
                console.log('   Response:', JSON.stringify(data, null, 2));
                return true;
            } else {
                console.log('❌ Proxy failed:', data.error);
                return false;
            }
        } catch (error) {
            console.log('❌ Proxy error:', error.message);
            return false;
        }
    }

    async testDataOperation() {
        console.log('\n📝 Testing Data Operation (List Tables)...');
        
        if (!this.sessionCookie || !this.csrfToken) {
            console.log('❌ Not authenticated. Please login first.');
            return false;
        }

        try {
            const response = await fetch(`${this.baseUrl}/api/proxy/tables`, {
                method: 'GET',
                headers: {
                    'X-CSRF-Token': this.csrfToken,
                    'Cookie': this.sessionCookie,
                    'X-Database-Name': 'test_db'
                }
            });

            const data = await response.json();
            
            if (response.ok) {
                console.log('✅ Data operation working');
                console.log('   Tables:', JSON.stringify(data, null, 2));
                return true;
            } else {
                console.log('❌ Data operation failed:', data.error);
                return false;
            }
        } catch (error) {
            console.log('❌ Data operation error:', error.message);
            return false;
        }
    }

    async testLogout() {
        console.log('\n📝 Testing Logout...');
        
        if (!this.sessionCookie) {
            console.log('❌ Not authenticated. Please login first.');
            return false;
        }

        try {
            const response = await fetch(`${this.baseUrl}/api/auth/logout`, {
                method: 'POST',
                headers: {
                    'Cookie': this.sessionCookie
                }
            });

            const data = await response.json();
            
            if (response.ok && data.success) {
                console.log('✅ Logout successful');
                this.sessionCookie = null;
                this.csrfToken = null;
                return true;
            } else {
                console.log('❌ Logout failed:', data.error);
                return false;
            }
        } catch (error) {
            console.log('❌ Logout error:', error.message);
            return false;
        }
    }

    async testSessionExpiry() {
        console.log('\n📝 Testing Session Expiry...');
        
        // Try to use an invalid session
        const oldCookie = this.sessionCookie;
        this.sessionCookie = 'vibe_session=invalid-session-id';
        
        try {
            const response = await fetch(`${this.baseUrl}/api/proxy/health`, {
                method: 'GET',
                headers: {
                    'X-CSRF-Token': this.csrfToken || 'invalid',
                    'Cookie': this.sessionCookie
                }
            });

            const data = await response.json();
            
            if (response.status === 401) {
                console.log('✅ Invalid session properly rejected');
                this.sessionCookie = oldCookie;
                return true;
            } else {
                console.log('❌ Invalid session not rejected properly');
                return false;
            }
        } catch (error) {
            console.log('❌ Session test error:', error.message);
            return false;
        }
    }
}

async function runTests() {
    console.log('=== Vibe Auth Gateway Test Suite ===\n');
    
    const url = await prompt('Enter gateway URL (or press Enter for localhost): ');
    const baseUrl = url || 'http://localhost:7071';
    
    const username = await prompt('Username: ');
    const password = await prompt('Password: ');
    
    const tester = new AuthTester(baseUrl);
    
    console.log(`\nTesting against: ${baseUrl}`);
    
    // Run tests
    const results = {
        login: await tester.testLogin(username, password),
        proxy: await tester.testProxy(),
        data: await tester.testDataOperation(),
        sessionExpiry: await tester.testSessionExpiry(),
        logout: await tester.testLogout()
    };
    
    // Summary
    console.log('\n=== Test Summary ===');
    console.log(`Login:          ${results.login ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Proxy:          ${results.proxy ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Data Op:        ${results.data ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Session Expiry: ${results.sessionExpiry ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Logout:         ${results.logout ? '✅ PASS' : '❌ FAIL'}`);
    
    const allPassed = Object.values(results).every(r => r);
    console.log(`\nOverall: ${allPassed ? '✅ ALL TESTS PASSED' : '❌ SOME TESTS FAILED'}`);
    
    rl.close();
}

// Run the tests
runTests().catch(console.error);