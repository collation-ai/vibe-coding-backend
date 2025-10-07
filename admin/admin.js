// Admin Dashboard JavaScript - Version 2.1 - Dynamic Database Loading
// Last Updated: 2025-10-06 - Added dynamic database selection from server
// Configuration
const API_BASE_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://vibe-coding-backend.azurewebsites.net';

let adminApiKey = null;
let currentUser = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check if already logged in
    const savedKey = localStorage.getItem('adminApiKey');
    if (savedKey) {
        adminApiKey = savedKey;
        validateAndShowDashboard();
    }
});

// Authentication
async function login(event) {
    event.preventDefault();
    const apiKey = document.getElementById('admin-api-key').value.trim();

    if (!apiKey) {
        showToast('Please enter an API key', 'error');
        return;
    }

    adminApiKey = apiKey;
    const isValid = await validateAndShowDashboard();

    if (isValid) {
        localStorage.setItem('adminApiKey', apiKey);
    }
}

async function validateAndShowDashboard() {
    try {
        const response = await apiRequest('/api/auth/validate', 'POST');

        if (response.success !== false) {
            currentUser = response.data.user;
            document.getElementById('admin-info').textContent = `👤 ${currentUser.email}`;
            document.getElementById('login-screen').style.display = 'none';
            document.getElementById('dashboard-screen').style.display = 'block';

            // Load initial data
            loadUsers();
            showToast('Welcome to Admin Dashboard!', 'success');
            return true;
        } else {
            showToast('Invalid API key', 'error');
            logout();
            return false;
        }
    } catch (error) {
        console.error('Validation error:', error);
        showToast('Failed to validate API key', 'error');
        logout();
        return false;
    }
}

function logout() {
    adminApiKey = null;
    currentUser = null;
    localStorage.removeItem('adminApiKey');
    document.getElementById('login-screen').style.display = 'block';
    document.getElementById('dashboard-screen').style.display = 'none';
}

// API Helper
async function apiRequest(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'X-API-Key': adminApiKey,
            'Content-Type': 'application/json'
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);

    if (response.status === 401) {
        showToast('Session expired. Please login again.', 'error');
        logout();
        throw new Error('Unauthorized');
    }

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error?.message || 'Request failed');
    }

    return data;
}

// Tab Navigation
function showTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load data for the tab
    switch(tabName) {
        case 'users':
            loadUsers();
            break;
        case 'api-keys':
            loadApiKeys();
            loadUserSelectOptions();
            break;
        case 'databases':
            loadDatabases();
            break;
        case 'db-servers':
            loadDbServers();
            break;
        case 'permissions':
            loadPermissions();
            loadUserSelectOptions();
            break;
        case 'pg-users':
            loadPgUsers();
            break;
        case 'table-permissions':
            loadTablePermissions();
            break;
        case 'rls-policies':
            loadRlsPolicies();
            break;
    }
}

// Users Management
async function loadUsers() {
    try {
        const response = await apiRequest('/api/admin/users', 'GET');
        const users = response.data || [];

        const tbody = document.querySelector('#users-table tbody');
        tbody.innerHTML = users.map(user => {
            const passwordExpired = user.password_expires_at && new Date(user.password_expires_at) < new Date();
            const passwordExpiryText = user.password_expires_at
                ? new Date(user.password_expires_at).toLocaleDateString()
                : 'Never';

            return `
            <tr>
                <td>
                    ${user.email}
                    ${passwordExpired ? '<br><span class="badge badge-warning">Password Expired</span>' : ''}
                    ${user.password_reset_required ? '<br><span class="badge badge-danger">Reset Required</span>' : ''}
                </td>
                <td>${user.organization || '-'}</td>
                <td>
                    <span class="badge ${user.is_active ? 'badge-success' : 'badge-danger'}">
                        ${user.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>
                    ${new Date(user.created_at).toLocaleDateString()}
                    <br><small>Pwd Expires: ${passwordExpiryText}</small>
                </td>
                <td>
                    <div class="action-buttons">
                        ${user.is_active
                            ? `<button class="btn-danger btn-sm" onclick="deactivateUser('${user.id}')">Deactivate</button>`
                            : `<button class="btn-success btn-sm" onclick="activateUser('${user.id}')">Activate</button>`
                        }
                        <button class="btn-warning btn-sm" onclick="sendPasswordReset('${user.id}', '${user.email}')">Reset Password</button>
                        <button class="btn-danger btn-sm" onclick="removeUser('${user.id}', '${user.email}')">Remove User</button>
                    </div>
                </td>
            </tr>
        `}).join('');
    } catch (error) {
        console.error('Failed to load users:', error);
        showToast('Failed to load users', 'error');
    }
}

async function createUser(event) {
    event.preventDefault();

    const email = document.getElementById('new-user-email').value;
    const username = document.getElementById('new-user-username').value || email;
    const password = document.getElementById('new-user-password').value;
    const organization = document.getElementById('new-user-org').value;

    try {
        await apiRequest('/api/admin/users', 'POST', {
            email,
            username,
            password,
            organization
        });

        closeModal('create-user-modal');
        showToast('User created successfully!', 'success');
        loadUsers();

        // Reset form
        event.target.reset();
    } catch (error) {
        showToast(error.message || 'Failed to create user', 'error');
    }
}

async function deactivateUser(userId) {
    if (!confirm('Are you sure you want to deactivate this user?')) return;

    try {
        await apiRequest(`/api/admin/users/${userId}/deactivate`, 'POST');
        showToast('User deactivated', 'success');
        loadUsers();
    } catch (error) {
        showToast('Failed to deactivate user', 'error');
    }
}

async function activateUser(userId) {
    try {
        await apiRequest(`/api/admin/users/${userId}/activate`, 'POST');
        showToast('User activated', 'success');
        loadUsers();
    } catch (error) {
        showToast('Failed to activate user', 'error');
    }
}

// API Keys Management
async function loadApiKeys() {
    try {
        const userFilter = document.getElementById('key-user-filter').value;
        const endpoint = userFilter
            ? `/api/admin/api-keys?user_id=${userFilter}`
            : '/api/admin/api-keys';

        const response = await apiRequest(endpoint, 'GET');
        const keys = response.data || [];

        const tbody = document.querySelector('#api-keys-table tbody');
        tbody.innerHTML = keys.map(key => `
            <tr>
                <td>${key.user_email}</td>
                <td>${key.name || '-'}</td>
                <td><code>${key.key_prefix}</code></td>
                <td>
                    <span class="badge ${key.is_active ? 'badge-success' : 'badge-danger'}">
                        ${key.is_active ? 'Active' : 'Revoked'}
                    </span>
                </td>
                <td>${key.last_used_at ? new Date(key.last_used_at).toLocaleString() : 'Never'}</td>
                <td>
                    ${key.is_active
                        ? `<button class="btn-danger" onclick="revokeApiKey('${key.id}')">Revoke</button>`
                        : '-'
                    }
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load API keys:', error);
        showToast('Failed to load API keys', 'error');
    }
}

async function createApiKey(event) {
    event.preventDefault();

    const userId = document.getElementById('key-user-select').value;
    const name = document.getElementById('key-name').value;
    const environment = document.getElementById('key-env').value;
    const expiresInDays = document.getElementById('key-expiry').value;

    try {
        const response = await apiRequest('/api/admin/api-keys', 'POST', {
            user_id: userId,
            name,
            environment,
            expires_in_days: expiresInDays ? parseInt(expiresInDays) : null
        });

        // Show the generated API key
        document.getElementById('generated-key').value = response.data.api_key;
        closeModal('create-key-modal');
        openModal('api-key-display-modal');

        event.target.reset();
        loadApiKeys();
    } catch (error) {
        showToast(error.message || 'Failed to generate API key', 'error');
    }
}

async function revokeApiKey(keyId) {
    if (!confirm('Are you sure you want to revoke this API key?')) return;

    try {
        await apiRequest(`/api/admin/api-keys/${keyId}/revoke`, 'POST');
        showToast('API key revoked', 'success');
        loadApiKeys();
    } catch (error) {
        showToast('Failed to revoke API key', 'error');
    }
}

function copyApiKey() {
    const input = document.getElementById('generated-key');
    input.select();
    document.execCommand('copy');
    showToast('API key copied to clipboard!', 'success');
}

// Database Assignments
async function loadDatabases() {
    try {
        const response = await apiRequest('/api/admin/database-assignments', 'GET');
        const assignments = response.data || [];

        const tbody = document.querySelector('#databases-table tbody');
        tbody.innerHTML = assignments.map(db => `
            <tr>
                <td>${db.user_email}</td>
                <td><code>${db.database_name}</code></td>
                <td>${new Date(db.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn-danger" onclick="removeDatabase('${db.id}')">Remove</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load databases:', error);
        showToast('Failed to load database assignments', 'error');
    }
}

async function assignDatabase(event) {
    event.preventDefault();

    const userId = document.getElementById('db-user-select').value;
    const databaseName = document.getElementById('db-name').value;
    const connectionString = document.getElementById('db-connection-string').value;

    try {
        await apiRequest('/api/admin/database-assignments', 'POST', {
            user_id: userId,
            database_name: databaseName,
            connection_string: connectionString
        });

        closeModal('assign-db-modal');
        showToast('Database assigned successfully!', 'success');
        loadDatabases();

        event.target.reset();
    } catch (error) {
        showToast(error.message || 'Failed to assign database', 'error');
    }
}

async function removeDatabase(assignmentId) {
    if (!confirm('Are you sure you want to remove this database assignment?')) return;

    try {
        await apiRequest(`/api/admin/database-assignments/${assignmentId}`, 'DELETE');
        showToast('Database assignment removed', 'success');
        loadDatabases();
    } catch (error) {
        showToast('Failed to remove database assignment', 'error');
    }
}

// Permissions Management
async function loadPermissions() {
    try {
        const userFilter = document.getElementById('perm-user-filter').value;
        const endpoint = userFilter
            ? `/api/admin/permissions?user_id=${userFilter}`
            : '/api/admin/permissions';

        const response = await apiRequest(endpoint, 'GET');
        const permissions = response.data || [];

        const tbody = document.querySelector('#permissions-table tbody');
        tbody.innerHTML = permissions.map(perm => `
            <tr>
                <td>${perm.user_email}</td>
                <td><code>${perm.database_name}</code></td>
                <td><code>${perm.schema_name}</code></td>
                <td>
                    <span class="badge ${perm.permission === 'read_write' ? 'badge-success' : 'badge-info'}">
                        ${perm.permission === 'read_write' ? 'Read & Write' : 'Read Only'}
                    </span>
                </td>
                <td>${new Date(perm.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn-danger" onclick="revokePermission('${perm.id}')">Revoke</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load permissions:', error);
        showToast('Failed to load permissions', 'error');
    }
}

async function grantPermission(event) {
    event.preventDefault();

    const userId = document.getElementById('perm-user-select').value;
    const databaseName = document.getElementById('perm-database-select').value;
    const schemaName = document.getElementById('perm-schema').value;
    const permission = document.getElementById('perm-level').value;

    try {
        await apiRequest('/api/admin/permissions', 'POST', {
            user_id: userId,
            database_name: databaseName,
            schema_name: schemaName,
            permission
        });

        closeModal('grant-permission-modal');
        showToast('Permission granted successfully!', 'success');
        loadPermissions();

        event.target.reset();
    } catch (error) {
        showToast(error.message || 'Failed to grant permission', 'error');
    }
}

async function revokePermission(permissionId) {
    if (!confirm('Are you sure you want to revoke this permission?')) return;

    try {
        await apiRequest(`/api/admin/permissions/${permissionId}`, 'DELETE');
        showToast('Permission revoked', 'success');
        loadPermissions();
    } catch (error) {
        showToast('Failed to revoke permission', 'error');
    }
}

async function loadUserDatabases(userId) {
    try {
        const select = document.getElementById('perm-database-select');

        if (!userId) {
            select.innerHTML = '<option value="">Select a user first</option>';
            return;
        }

        const response = await apiRequest(`/api/admin/users/${userId}/databases`, 'GET');
        const databases = response.data || [];

        if (databases.length === 0) {
            select.innerHTML = '<option value="">No databases assigned to this user</option>';
        } else {
            select.innerHTML = databases.map(db =>
                `<option value="${db.database_name}">${db.database_name}</option>`
            ).join('');
        }
    } catch (error) {
        console.error('Failed to load user databases:', error);
        const select = document.getElementById('perm-database-select');
        select.innerHTML = '<option value="">Error loading databases</option>';
    }
}

// Helper: Load user options for select dropdowns
async function loadUserSelectOptions() {
    try {
        const response = await apiRequest('/api/admin/users', 'GET');
        const users = response.data || [];

        // Update all user select dropdowns
        const selects = [
            'key-user-select',
            'db-user-select',
            'perm-user-select',
            'key-user-filter',
            'perm-user-filter',
            'pg-user-select',
            'table-perm-user-select',
            'rls-user-select'
        ];

        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                const isFilter = selectId.includes('filter');
                const options = users.map(user =>
                    `<option value="${user.id}">${user.email}</option>`
                ).join('');

                select.innerHTML = isFilter
                    ? `<option value="">All Users</option>${options}`
                    : options;
            }
        });
    } catch (error) {
        console.error('Failed to load users for select:', error);
    }
}

// Modal Helpers
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function showCreateUserModal() {
    openModal('create-user-modal');
}

function showCreateKeyModal() {
    loadUserSelectOptions();
    openModal('create-key-modal');
}

function showAssignDbModal() {
    loadUserSelectOptions();
    openModal('assign-db-modal');
}

function showGrantPermissionModal() {
    loadUserSelectOptions();
    // Initialize database dropdown with prompt
    const dbSelect = document.getElementById('perm-database-select');
    if (dbSelect) {
        dbSelect.innerHTML = '<option value="">Select a user first</option>';
    }
    openModal('grant-permission-modal');
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

// Toast Notifications
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// PostgreSQL Users Management
async function loadPgUsers() {
    try {
        const response = await apiRequest('/api/admin/pg-users', 'GET');
        const pgUsers = response.data || [];

        const tbody = document.querySelector('#pg-users-table tbody');
        tbody.innerHTML = pgUsers.map(user => `
            <tr>
                <td>${user.user_email}</td>
                <td><code>${user.database_name}</code></td>
                <td><code>${user.pg_username}</code></td>
                <td>
                    <span class="badge ${user.is_active ? 'badge-success' : 'badge-danger'}">
                        ${user.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>${new Date(user.created_at).toLocaleDateString()}</td>
                <td>${user.notes || '-'}</td>
                <td>
                    ${user.is_active
                        ? `<button class="btn-danger" onclick="dropPgUser('${user.vibe_user_id}', '${user.database_name}')">Drop User</button>`
                        : '-'
                    }
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load PG users:', error);
        showToast('Failed to load PG users', 'error');
    }
}

async function showCreatePgUserModal() {
    await loadUserSelectOptions();
    await loadDbServerOptions('pg-stored-server');
    // Database list will be loaded when server is selected
    const dbSelect = document.getElementById('pg-database-select');
    if (dbSelect) {
        dbSelect.innerHTML = '<option value="">Select a database server first</option>';
    }
    openModal('create-pg-user-modal');
}

async function loadDatabasesFromServer(serverId, selectElementId) {
    console.log('📂 loadDatabasesFromServer called with:', { serverId, selectElementId });
    try {
        const select = document.getElementById(selectElementId);
        console.log('Select element found:', !!select);
        if (!select) {
            console.error('Select element not found:', selectElementId);
            return;
        }

        if (!serverId) {
            console.log('No server ID provided');
            select.innerHTML = '<option value="">Select a database server first</option>';
            return;
        }

        // Show loading state
        console.log('Setting loading state...');
        select.innerHTML = '<option value="">Loading databases...</option>';

        console.log('Fetching databases from API...');
        const response = await apiRequest(`/api/admin/database-servers/${serverId}/databases`, 'GET');
        console.log('API response:', response);
        const databases = response.data || [];
        console.log('Databases received:', databases);

        if (databases.length === 0) {
            select.innerHTML = '<option value="">No databases found on this server</option>';
        } else {
            select.innerHTML = databases.map(db =>
                `<option value="${db}">${db}</option>`
            ).join('');
            console.log(`✅ Loaded ${databases.length} databases`);
        }
    } catch (error) {
        console.error('❌ Failed to load databases from server:', error);
        const select = document.getElementById(selectElementId);
        if (select) {
            select.innerHTML = '<option value="">Error loading databases</option>';
        }
        showToast('Failed to load databases from server: ' + error.message, 'error');
    }
}

// Legacy function for backward compatibility
async function loadDatabaseOptionsForPgUser() {
    // This is now handled by loadDatabasesFromServer when server is selected
    const dbSelect = document.getElementById('pg-database-select');
    if (dbSelect) {
        dbSelect.innerHTML = '<option value="">Select a database server first</option>';
    }
}

async function createPgUser(event) {
    event.preventDefault();

    const userId = document.getElementById('pg-user-select').value;
    const databaseName = document.getElementById('pg-database-select').value;
    const credType = document.getElementById('pg-cred-type').value;
    const notes = document.getElementById('pg-user-notes').value;

    let adminConnection;

    try {
        // Get connection string based on credential type
        if (credType === 'stored') {
            const serverId = document.getElementById('pg-stored-server').value;
            adminConnection = await getConnectionStringFromServer(serverId, databaseName);
        } else {
            adminConnection = document.getElementById('pg-admin-connection').value;
        }

        await apiRequest('/api/admin/pg-users', 'POST', {
            user_id: userId,
            database_name: databaseName,
            admin_connection_string: adminConnection,
            notes: notes || null
        });

        closeModal('create-pg-user-modal');
        showToast('PostgreSQL user created successfully!', 'success');
        loadPgUsers();

        event.target.reset();
    } catch (error) {
        showToast(error.message || 'Failed to create PG user', 'error');
    }
}

async function dropPgUser(userId, databaseName) {
    if (!confirm('Are you sure you want to drop this PostgreSQL user? This will revoke all their privileges.')) return;

    try {
        await apiRequest(`/api/admin/pg-users/${userId}/${databaseName}`, 'DELETE');
        showToast('PostgreSQL user dropped successfully!', 'success');
        loadPgUsers();
    } catch (error) {
        showToast(error.message || 'Failed to drop PG user', 'error');
    }
}

// Table Permissions Management
async function loadTablePermissions() {
    try {
        const response = await apiRequest('/api/admin/table-permissions', 'GET');
        const permissions = response.data || [];

        const tbody = document.querySelector('#table-permissions-table tbody');
        tbody.innerHTML = permissions.map(perm => {
            const perms = [];
            if (perm.can_select) perms.push('SELECT');
            if (perm.can_insert) perms.push('INSERT');
            if (perm.can_update) perms.push('UPDATE');
            if (perm.can_delete) perms.push('DELETE');
            if (perm.can_truncate) perms.push('TRUNCATE');
            if (perm.can_references) perms.push('REFERENCES');
            if (perm.can_trigger) perms.push('TRIGGER');

            return `
                <tr>
                    <td>${perm.user_email}</td>
                    <td><code>${perm.database_name}</code></td>
                    <td><code>${perm.schema_name}.${perm.table_name}</code></td>
                    <td>${perms.join(', ') || 'None'}</td>
                    <td>${perm.column_permissions ? 'Yes' : 'No'}</td>
                    <td>${new Date(perm.created_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn-danger" onclick="revokeTablePermission('${perm.id}')">Revoke</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load table permissions:', error);
        showToast('Failed to load table permissions', 'error');
    }
}

async function showGrantTablePermissionModal() {
    await loadUserSelectOptions();
    await loadDbServerOptions('table-perm-stored-server');
    openModal('grant-table-permission-modal');
}

async function grantTablePermission(event) {
    event.preventDefault();

    const userId = document.getElementById('table-perm-user-select').value;
    const database = document.getElementById('table-perm-database').value;
    const credType = document.getElementById('table-perm-cred-type').value;
    const schema = document.getElementById('table-perm-schema').value;
    const table = document.getElementById('table-perm-table').value;

    let adminConnection;

    try {
        // Get connection string based on credential type
        if (credType === 'stored') {
            const serverId = document.getElementById('table-perm-stored-server').value;
            adminConnection = await getConnectionStringFromServer(serverId, database);
        } else {
            adminConnection = document.getElementById('table-perm-admin-connection').value;
        }

        await apiRequest('/api/admin/table-permissions', 'POST', {
            user_id: userId,
            database_name: database,
            admin_connection_string: adminConnection,
            schema_name: schema,
            table_name: table,
            can_select: document.getElementById('table-perm-select').checked,
            can_insert: document.getElementById('table-perm-insert').checked,
            can_update: document.getElementById('table-perm-update').checked,
            can_delete: document.getElementById('table-perm-delete').checked,
            can_truncate: document.getElementById('table-perm-truncate').checked,
            can_references: document.getElementById('table-perm-references').checked,
            can_trigger: document.getElementById('table-perm-trigger').checked
        });

        closeModal('grant-table-permission-modal');
        showToast('Table permissions granted successfully!', 'success');
        loadTablePermissions();

        event.target.reset();
    } catch (error) {
        showToast(error.message || 'Failed to grant table permissions', 'error');
    }
}

async function revokeTablePermission(permissionId) {
    if (!confirm('Are you sure you want to revoke this table permission?')) return;

    try {
        await apiRequest(`/api/admin/table-permissions/${permissionId}`, 'DELETE');
        showToast('Table permission revoked', 'success');
        loadTablePermissions();
    } catch (error) {
        showToast('Failed to revoke table permission', 'error');
    }
}

// RLS Policies Management
async function loadRlsPolicies() {
    try {
        const response = await apiRequest('/api/admin/rls-policies', 'GET');
        const policies = response.data || [];

        const tbody = document.querySelector('#rls-policies-table tbody');
        tbody.innerHTML = policies.map(policy => `
            <tr>
                <td>${policy.user_email}</td>
                <td><code>${policy.database_name}</code></td>
                <td><code>${policy.schema_name}.${policy.table_name}</code></td>
                <td><code>${policy.policy_name}</code></td>
                <td>
                    <span class="badge badge-info">${policy.policy_type}</span>
                    <span class="badge badge-${policy.command_type === 'PERMISSIVE' ? 'success' : 'warning'}">${policy.command_type}</span>
                </td>
                <td><code>${policy.using_expression.substring(0, 40)}${policy.using_expression.length > 40 ? '...' : ''}</code></td>
                <td>${policy.template_used || '-'}</td>
                <td>${new Date(policy.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn-danger" onclick="dropRlsPolicy('${policy.id}', '${policy.database_name}')">Drop</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load RLS policies:', error);
        showToast('Failed to load RLS policies', 'error');
    }
}

async function showCreateRlsPolicyModal() {
    await loadUserSelectOptions();
    await loadDbServerOptions('rls-stored-server');
    openModal('create-rls-policy-modal');
}

async function createRlsPolicy(event) {
    event.preventDefault();

    const userId = document.getElementById('rls-user-select').value;
    const database = document.getElementById('rls-database').value;
    const credType = document.getElementById('rls-cred-type').value;
    const schema = document.getElementById('rls-schema').value;
    const table = document.getElementById('rls-table').value;
    const policyName = document.getElementById('rls-policy-name').value;
    const policyType = document.getElementById('rls-policy-type').value;
    const commandType = document.getElementById('rls-command-type').value;
    const usingExpression = document.getElementById('rls-using-expression').value;
    const withCheckExpression = document.getElementById('rls-with-check-expression').value;
    const templateUsed = document.getElementById('rls-template-used').value;
    const notes = document.getElementById('rls-notes').value;

    let adminConnection;

    try {
        // Get connection string based on credential type
        if (credType === 'stored') {
            const serverId = document.getElementById('rls-stored-server').value;
            adminConnection = await getConnectionStringFromServer(serverId, database);
        } else {
            adminConnection = document.getElementById('rls-admin-connection').value;
        }

        await apiRequest('/api/admin/rls-policies', 'POST', {
            user_id: userId,
            database_name: database,
            admin_connection_string: adminConnection,
            schema_name: schema,
            table_name: table,
            policy_name: policyName,
            policy_type: policyType,
            command_type: commandType,
            using_expression: usingExpression,
            with_check_expression: withCheckExpression || null,
            template_used: templateUsed || null,
            notes: notes || null
        });

        closeModal('create-rls-policy-modal');
        showToast('RLS policy created successfully!', 'success');
        loadRlsPolicies();

        event.target.reset();
    } catch (error) {
        showToast(error.message || 'Failed to create RLS policy', 'error');
    }
}

async function dropRlsPolicy(policyId, databaseName) {
    if (!confirm('Are you sure you want to drop this RLS policy?')) return;

    const adminConnection = prompt('Enter admin connection string for ' + databaseName + ':');
    if (!adminConnection) return;

    try {
        await apiRequest(`/api/admin/rls-policies/${policyId}?admin_connection_string=${encodeURIComponent(adminConnection)}`, 'DELETE');
        showToast('RLS policy dropped', 'success');
        loadRlsPolicies();
    } catch (error) {
        showToast('Failed to drop RLS policy', 'error');
    }
}

async function showRlsTemplatesModal() {
    try {
        const response = await apiRequest('/api/admin/rls-templates', 'GET');
        const templates = response.data || [];

        const list = document.getElementById('rls-templates-list');
        list.innerHTML = templates.map(template => `
            <div style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px;">
                <h3 style="margin-top: 0; color: #667eea;">${template.template_name}</h3>
                <p style="color: #495057;">${template.description}</p>
                <p><strong>Policy Type:</strong> ${template.policy_type}</p>
                <p><strong>USING Expression:</strong><br><code style="background: #e9ecef; padding: 5px; border-radius: 3px; display: block; margin-top: 5px;">${template.using_expression_template}</code></p>
                ${template.with_check_expression_template ? `<p><strong>WITH CHECK Expression:</strong><br><code style="background: #e9ecef; padding: 5px; border-radius: 3px; display: block; margin-top: 5px;">${template.with_check_expression_template}</code></p>` : ''}
                <p><strong>Required Columns:</strong> ${JSON.parse(template.required_columns).join(', ')}</p>
                <p style="font-style: italic; color: #6c757d;">${template.example_usage}</p>
            </div>
        `).join('');

        openModal('rls-templates-modal');
    } catch (error) {
        console.error('Failed to load RLS templates:', error);
        showToast('Failed to load RLS templates', 'error');
    }
}

// Database Servers Management
async function loadDbServers() {
    try {
        const response = await apiRequest('/api/admin/database-servers', 'GET');
        const servers = response.data || [];

        const tbody = document.querySelector('#db-servers-table tbody');
        tbody.innerHTML = servers.map(server => `
            <tr>
                <td><strong>${server.server_name}</strong></td>
                <td>${server.host}</td>
                <td>${server.port}</td>
                <td>${server.admin_username}</td>
                <td>${server.ssl_mode}</td>
                <td>
                    <span class="badge ${server.is_active ? 'badge-success' : 'badge-danger'}">
                        ${server.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>${new Date(server.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn-danger" onclick="deleteDbServer('${server.id}')">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load database servers:', error);
        showToast('Failed to load database servers', 'error');
    }
}

function showCreateDbServerModal() {
    openModal('create-db-server-modal');
}

async function createDbServer(event) {
    event.preventDefault();

    const serverName = document.getElementById('db-server-name').value;
    const host = document.getElementById('db-server-host').value;
    const port = parseInt(document.getElementById('db-server-port').value);
    const username = document.getElementById('db-server-username').value;
    const password = document.getElementById('db-server-password').value;
    const sslMode = document.getElementById('db-server-ssl').value;
    const notes = document.getElementById('db-server-notes').value;

    try {
        await apiRequest('/api/admin/database-servers', 'POST', {
            server_name: serverName,
            host: host,
            port: port,
            admin_username: username,
            admin_password: password,
            ssl_mode: sslMode,
            notes: notes || null
        });

        closeModal('create-db-server-modal');
        showToast('Database server added successfully!', 'success');
        loadDbServers();

        event.target.reset();
    } catch (error) {
        showToast(error.message || 'Failed to add database server', 'error');
    }
}

async function deleteDbServer(serverId) {
    if (!confirm('Are you sure you want to delete this database server? This will not affect existing PG users.')) return;

    try {
        await apiRequest(`/api/admin/database-servers/${serverId}`, 'DELETE');
        showToast('Database server deleted', 'success');
        loadDbServers();
    } catch (error) {
        showToast('Failed to delete database server', 'error');
    }
}

async function loadDbServerOptions(selectId) {
    try {
        const response = await apiRequest('/api/admin/database-servers', 'GET');
        const servers = response.data || [];

        const select = document.getElementById(selectId);
        if (select) {
            select.innerHTML = '<option value="">Select a server...</option>' + servers.map(server =>
                `<option value="${server.id}">${server.server_name} (${server.host})</option>`
            ).join('');

            // Add event listener programmatically if this is the PG user server select
            if (selectId === 'pg-stored-server') {
                console.log('Adding onchange listener to pg-stored-server');
                select.onchange = onPgServerSelected;
            }
        }
    } catch (error) {
        console.error('Failed to load server options:', error);
    }
}

// Toggle functions for credential input
function togglePgCredentialInput() {
    const credType = document.getElementById('pg-cred-type').value;
    const storedGroup = document.getElementById('pg-stored-server-group');
    const customGroup = document.getElementById('pg-custom-connection-group');
    const dbSelect = document.getElementById('pg-database-select');

    if (credType === 'stored') {
        storedGroup.style.display = 'block';
        customGroup.style.display = 'none';
        document.getElementById('pg-stored-server').required = true;
        document.getElementById('pg-admin-connection').required = false;

        // Load server options and reset database dropdown
        loadDbServerOptions('pg-stored-server');
        if (dbSelect) {
            dbSelect.innerHTML = '<option value="">Select a database server first</option>';
        }
    } else {
        storedGroup.style.display = 'none';
        customGroup.style.display = 'block';
        document.getElementById('pg-stored-server').required = false;
        document.getElementById('pg-admin-connection').required = true;

        // For custom connection, show manual input prompt
        if (dbSelect) {
            dbSelect.innerHTML = '<option value="">Enter database name below</option>';
        }
    }
}

// Event handler for when database server is selected
function onPgServerSelected() {
    console.log('🔄 Server selected, loading databases...');
    const serverId = document.getElementById('pg-stored-server').value;
    console.log('Selected server ID:', serverId);
    if (serverId) {
        loadDatabasesFromServer(serverId, 'pg-database-select');
    } else {
        console.log('No server selected');
    }
}

function toggleTablePermCredentialInput() {
    const credType = document.getElementById('table-perm-cred-type').value;
    const storedGroup = document.getElementById('table-perm-stored-server-group');
    const customGroup = document.getElementById('table-perm-custom-connection-group');

    if (credType === 'stored') {
        storedGroup.style.display = 'block';
        customGroup.style.display = 'none';
        document.getElementById('table-perm-stored-server').required = true;
        document.getElementById('table-perm-admin-connection').required = false;
        loadDbServerOptions('table-perm-stored-server');
    } else {
        storedGroup.style.display = 'none';
        customGroup.style.display = 'block';
        document.getElementById('table-perm-stored-server').required = false;
        document.getElementById('table-perm-admin-connection').required = true;
    }
}

function toggleRlsCredentialInput() {
    const credType = document.getElementById('rls-cred-type').value;
    const storedGroup = document.getElementById('rls-stored-server-group');
    const customGroup = document.getElementById('rls-custom-connection-group');

    if (credType === 'stored') {
        storedGroup.style.display = 'block';
        customGroup.style.display = 'none';
        document.getElementById('rls-stored-server').required = true;
        document.getElementById('rls-admin-connection').required = false;
        loadDbServerOptions('rls-stored-server');
    } else {
        storedGroup.style.display = 'none';
        customGroup.style.display = 'block';
        document.getElementById('rls-stored-server').required = false;
        document.getElementById('rls-admin-connection').required = true;
    }
}

async function getConnectionStringFromServer(serverId, databaseName) {
    try {
        const response = await apiRequest(
            `/api/admin/database-servers/${serverId}/connection-string?database_name=${encodeURIComponent(databaseName)}`,
            'GET'
        );
        return response.data.connection_string;
    } catch (error) {
        console.error('Failed to get connection string:', error);
        throw error;
    }
}

// Password Reset & User Removal Functions
async function sendPasswordReset(userId, email) {
    if (!confirm(`Send password reset email to ${email}?`)) {
        return;
    }

    try {
        const response = await apiRequest('/api/auth/request-password-reset', 'POST', {
            email: email
        });

        if (response.success) {
            showToast(`Password reset email sent to ${email}`, 'success');
        } else {
            showToast('Failed to send password reset email', 'error');
        }
    } catch (error) {
        console.error('Failed to send password reset:', error);
        showToast('Failed to send password reset email', 'error');
    }
}

async function removeUser(userId, email) {
    const confirmMessage = `⚠️ WARNING: This will permanently remove user ${email} and:\n\n` +
        `• Drop all PostgreSQL users for this user\n` +
        `• Revoke all database permissions\n` +
        `• Drop all RLS policies\n` +
        `• Deactivate the account\n\n` +
        `This action CANNOT be undone!\n\n` +
        `Type the email address to confirm: ${email}`;

    const userInput = prompt(confirmMessage);

    if (userInput !== email) {
        if (userInput !== null) {
            showToast('Email confirmation did not match. User removal cancelled.', 'warning');
        }
        return;
    }

    try {
        const response = await apiRequest('/api/admin/remove-user', 'POST', {
            user_id: userId,
            admin_user_id: currentUser.id,
            cleanup_type: 'full_removal'
        });

        if (response.success) {
            const stats = response.cleanup_details;
            const message = `User ${email} removed successfully!\n\n` +
                `• PostgreSQL users dropped: ${stats.pg_users_dropped}\n` +
                `• Schema permissions revoked: ${stats.schema_permissions_revoked}\n` +
                `• Table permissions revoked: ${stats.table_permissions_revoked}\n` +
                `• RLS policies dropped: ${stats.rls_policies_dropped}\n` +
                `• Databases affected: ${stats.databases_affected.length}`;

            alert(message);
            showToast('User removed successfully', 'success');
            loadUsers();
        } else {
            showToast('Failed to remove user', 'error');
        }
    } catch (error) {
        console.error('Failed to remove user:', error);
        showToast(`Failed to remove user: ${error.message}`, 'error');
    }
}
