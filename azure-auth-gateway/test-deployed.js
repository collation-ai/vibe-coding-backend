const https = require('https');

async function testLogin() {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify({
            username: 'tanmais',
            password: 'Login123#'
        });

        const options = {
            hostname: 'vibe-auth-gateway.azurewebsites.net',
            port: 443,
            path: '/api/auth/login',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': data.length
            }
        };

        console.log('Testing login endpoint...');
        console.log(`POST https://${options.hostname}${options.path}`);
        console.log('Request body:', JSON.parse(data));
        console.log('');

        const req = https.request(options, (res) => {
            let responseData = '';

            res.on('data', (chunk) => {
                responseData += chunk;
            });

            res.on('end', () => {
                console.log(`Response Status: ${res.statusCode}`);
                console.log('Response Headers:', res.headers);
                console.log('Response Body:', responseData);
                
                if (res.statusCode === 200) {
                    console.log('\n✅ Login successful!');
                } else {
                    console.log('\n❌ Login failed');
                }
                resolve();
            });
        });

        req.on('error', (error) => {
            console.error('Request error:', error);
            reject(error);
        });

        req.write(data);
        req.end();
    });
}

// Run the test
testLogin().catch(console.error);