// Tijara Knowledge Graph - Admin Panel JavaScript

const API_BASE = 'http://127.0.0.1:8080';
console.log('[Admin.js] Loaded. API_BASE:', API_BASE);
let allRoles = [];
let allUsers = [];
let allPermissions = [];

// Toast notifications
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Tabs
document.querySelectorAll('.tab-button').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`${tab}-tab`).classList.add('active');
    });
});

// Modal functions
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Load statistics
async function loadStats() {
    try {
        const [usersResp, rolesResp, permsResp] = await Promise.all([
            authenticatedFetch(`${API_BASE}/admin/users`),
            authenticatedFetch(`${API_BASE}/admin/roles`),
            authenticatedFetch(`${API_BASE}/admin/permissions`)
        ]);

        const users = await usersResp.json();
        const roles = await rolesResp.json();
        const perms = await permsResp.json();

        document.getElementById('statsGrid').innerHTML = `
            <div class="stat-card">
                <div class="stat-icon users"><i class="fas fa-users"></i></div>
                <div class="stat-content">
                    <h3>${users.users.length}</h3>
                    <p>Total Users</p>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon roles"><i class="fas fa-user-tag"></i></div>
                <div class="stat-content">
                    <h3>${roles.roles.length}</h3>
                    <p>System Roles</p>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon permissions"><i class="fas fa-key"></i></div>
                <div class="stat-content">
                    <h3>${perms.permissions.length}</h3>
                    <p>Permissions</p>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Failed to load stats:', error);
        document.getElementById('statsGrid').innerHTML = '<p>Failed to load statistics</p>';
    }
}

// Load users
async function loadUsers() {
    console.log('[Admin.js] loadUsers called, fetching from:', `${API_BASE}/admin/users`);
    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/users`);
        console.log('[Admin.js] loadUsers response:', response);
        const data = await response.json();
        allUsers = data.users;

        let html = `
            <table class="table">
                <thead>
                    <tr>
                        <th>Username</th>
                        <th>Full Name</th>
                        <th>Email</th>
                        <th>Roles</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.users.forEach(user => {
            const rolesBadges = user.roles.map(r => `<span class="badge badge-${r}">${r}</span>`).join('');
            const superBadge = user.is_superuser ? '<span class="badge badge-superuser">Superuser</span>' : '';
            const statusBadge = user.is_active
                ? '<span class="badge badge-active">Active</span>'
                : '<span class="badge badge-inactive">Inactive</span>';

            html += `
                <tr>
                    <td><strong>${user.username}</strong></td>
                    <td>${user.full_name || '-'}</td>
                    <td>${user.email || '-'}</td>
                    <td>${rolesBadges} ${superBadge}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn btn-small btn-secondary" onclick="openEditUserModal('${user.username}')">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-small btn-primary" onclick="openAssignRoleModal('${user.username}')">
                                <i class="fas fa-user-tag"></i>
                            </button>
                            ${!user.is_superuser || user.username !== 'admin' ? `
                            <button class="btn btn-small btn-danger" onclick="deleteUser('${user.username}')">
                                <i class="fas fa-trash"></i>
                            </button>
                            ` : ''}
                        </div>
                    </td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        document.getElementById('usersContainer').innerHTML = html;
    } catch (error) {
        console.error('Failed to load users:', error);
        document.getElementById('usersContainer').innerHTML = '<p>Failed to load users</p>';
    }
}

// Load roles
async function loadRoles() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/roles`);
        const data = await response.json();
        allRoles = data.roles;

        let html = `
            <div style="margin-bottom: 1rem;">
                <button class="btn btn-primary" onclick="openCreateRoleModal()">
                    <i class="fas fa-plus"></i> Create Role
                </button>
            </div>
            <div class="role-grid">
        `;
        data.roles.forEach(role => {
            const permTags = role.permissions.map(p => `<span class="permission-tag">${p}</span>`).join('');
            const isSystem = role.is_system !== undefined ? role.is_system : ['admin', 'analyst', 'trader', 'data_engineer', 'viewer'].includes(role.name);
            html += `
                <div class="role-card">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <h3>${role.name}${isSystem ? ' <span class="badge badge-admin">System</span>' : ''}</h3>
                        ${!isSystem ? `
                        <div class="action-buttons">
                            <button class="btn btn-small btn-secondary" onclick="openEditRoleModal('${role.name}')">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-small btn-danger" onclick="deleteRole('${role.name}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                        ` : ''}
                    </div>
                    <p>${role.description || 'No description'}</p>
                    <div class="permission-list">${permTags || '<em>No permissions</em>'}</div>
                </div>
            `;
        });
        html += '</div>';
        document.getElementById('rolesContainer').innerHTML = html;
    } catch (error) {
        console.error('Failed to load roles:', error);
        document.getElementById('rolesContainer').innerHTML = '<p>Failed to load roles</p>';
    }
}

// Load permissions
async function loadPermissions() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/permissions`);
        const data = await response.json();
        allPermissions = data.permissions;

        let html = `
            <div style="margin-bottom: 1rem;">
                <button class="btn btn-primary" onclick="openCreatePermissionModal()">
                    <i class="fas fa-plus"></i> Create Permission
                </button>
            </div>
            <table class="table">
                <thead>
                    <tr>
                        <th>Permission Name</th>
                        <th>Resource</th>
                        <th>Action</th>
                        <th>Description</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.permissions.forEach(perm => {
            html += `
                <tr>
                    <td><strong>${perm.name}</strong></td>
                    <td>${perm.resource}</td>
                    <td>${perm.action}</td>
                    <td>${perm.description || '-'}</td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn btn-small btn-secondary" onclick="openEditPermissionModal('${perm.name}')">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-small btn-danger" onclick="deletePermission('${perm.name}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        document.getElementById('permissionsContainer').innerHTML = html;
    } catch (error) {
        console.error('Failed to load permissions:', error);
        document.getElementById('permissionsContainer').innerHTML = '<p>Failed to load permissions</p>';
    }
}

// Create user
function openCreateUserModal() {
    document.getElementById('createUserForm').reset();
    openModal('createUserModal');
}

async function createUser(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = {
        username: formData.get('username'),
        password: formData.get('password'),
        full_name: formData.get('full_name'),
        email: formData.get('email'),
        is_superuser: formData.get('is_superuser') === 'on'
    };

    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        showToast(result.message, 'success');
        closeModal('createUserModal');
        loadUsers();
        loadStats();
    } catch (error) {
        showToast(`Failed to create user: ${error.message}`, 'error');
    }
}

// Edit user
function openEditUserModal(username) {
    const user = allUsers.find(u => u.username === username);
    if (!user) return;

    document.getElementById('edit_username').value = username;
    document.getElementById('edit_full_name').value = user.full_name || '';
    document.getElementById('edit_email').value = user.email || '';
    document.getElementById('edit_is_active').checked = user.is_active;
    document.getElementById('edit_is_superuser').checked = user.is_superuser;
    openModal('editUserModal');
}

async function updateUser(event) {
    event.preventDefault();
    const username = document.getElementById('edit_username').value;
    const data = {
        full_name: document.getElementById('edit_full_name').value || null,
        email: document.getElementById('edit_email').value || null,
        is_active: document.getElementById('edit_is_active').checked,
        is_superuser: document.getElementById('edit_is_superuser').checked
    };

    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/users/${username}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        showToast(result.message, 'success');
        closeModal('editUserModal');
        loadUsers();
    } catch (error) {
        showToast(`Failed to update user: ${error.message}`, 'error');
    }
}

// Assign role
function openAssignRoleModal(username) {
    document.getElementById('assign_username').value = username;
    const select = document.getElementById('assign_role_name');
    select.innerHTML = '<option value="">-- Select Role --</option>';
    allRoles.forEach(role => {
        select.innerHTML += `<option value="${role.name}">${role.name}</option>`;
    });
    openModal('assignRoleModal');
}

async function assignRole(event) {
    event.preventDefault();
    const username = document.getElementById('assign_username').value;
    const role_name = document.getElementById('assign_role_name').value;

    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/users/${username}/roles`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, role_name })
        });

        const result = await response.json();
        showToast(result.message, 'success');
        closeModal('assignRoleModal');
        loadUsers();
    } catch (error) {
        showToast(`Failed to assign role: ${error.message}`, 'error');
    }
}

// Delete user
async function deleteUser(username) {
    if (!confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/users/${username}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        showToast(result.message, 'success');
        loadUsers();
        loadStats();
    } catch (error) {
        showToast(`Failed to delete user: ${error.message}`, 'error');
    }
}

// Initialize
async function init() {
    await loadStats();
    await loadUsers();
    await loadRoles();
    await loadPermissions();
}

init();

// ==================== Role Management ====================

function openCreateRoleModal() {
    document.getElementById('createRoleForm').reset();
    // Populate permission checkboxes
    const container = document.getElementById('rolePermissions');
    container.innerHTML = '';
    allRoles.length > 0 && loadRolePermissionCheckboxes();
    openModal('createRoleModal');
}

async function loadRolePermissionCheckboxes() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/permissions`);
        const data = await response.json();
        
        const container = document.getElementById('rolePermissions');
        container.innerHTML = '<h4>Permissions:</h4>';
        data.permissions.forEach(perm => {
            container.innerHTML += `
                <div class="checkbox-group">
                    <input type="checkbox" name="permission" value="${perm.name}" id="perm_${perm.name.replace(/:/g, '_')}">
                    <label for="perm_${perm.name.replace(/:/g, '_')}">${perm.name} - ${perm.description}</label>
                </div>
            `;
        });
    } catch (error) {
        console.error('Failed to load permissions:', error);
    }
}

async function createRole(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const permissions = Array.from(formData.getAll('permission'));
    
    const data = {
        name: formData.get('name'),
        description: formData.get('description'),
        permissions: permissions
    };

    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/roles`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        showToast(result.message, 'success');
        closeModal('createRoleModal');
        loadRoles();
        loadStats();
    } catch (error) {
        showToast(`Failed to create role: ${error.message}`, 'error');
    }
}

async function openEditRoleModal(roleName) {
    const role = allRoles.find(r => r.name === roleName);
    if (!role) return;

    document.getElementById('edit_role_name').value = roleName;
    document.getElementById('edit_role_name_display').value = roleName;
    document.getElementById('edit_role_description').value = role.description || '';
    
    // Load all permissions and check the ones this role has
    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/permissions`);
        const data = await response.json();
        
        const container = document.querySelector('#editRolePermissions > div');
        container.innerHTML = '';
        
        data.permissions.forEach(perm => {
            const isChecked = role.permissions.includes(perm.name);
            container.innerHTML += `
                <div class="checkbox-group">
                    <input type="checkbox" name="permission" value="${perm.name}" id="edit_perm_${perm.name.replace(/:/g, '_')}" ${isChecked ? 'checked' : ''}>
                    <label for="edit_perm_${perm.name.replace(/:/g, '_')}">${perm.name} - ${perm.description || 'No description'}</label>
                </div>
            `;
        });
    } catch (error) {
        console.error('Failed to load permissions:', error);
    }
    
    openModal('editRoleModal');
}

async function updateRole(event) {
    event.preventDefault();
    const roleName = document.getElementById('edit_role_name').value;
    const formData = new FormData(event.target);
    
    // Get selected permissions
    const selectedPermissions = Array.from(formData.getAll('permission'));
    const role = allRoles.find(r => r.name === roleName);
    const currentPermissions = role ? role.permissions : [];
    
    // Update description
    const data = {
        description: document.getElementById('edit_role_description').value || null
    };

    try {
        // Update role description
        const response = await authenticatedFetch(`${API_BASE}/admin/roles/${roleName}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        await response.json();
        
        // Find permissions to add and remove
        const toAdd = selectedPermissions.filter(p => !currentPermissions.includes(p));
        const toRemove = currentPermissions.filter(p => !selectedPermissions.includes(p));
        
        // Add new permissions
        for (const permName of toAdd) {
            const formData = new FormData();
            formData.append('permission_name', permName);
            await authenticatedFetch(`${API_BASE}/admin/roles/${roleName}/permissions`, {
                method: 'POST',
                body: formData
            });
        }
        
        // Remove permissions
        for (const permName of toRemove) {
            await authenticatedFetch(`${API_BASE}/admin/roles/${roleName}/permissions/${permName}`, {
                method: 'DELETE'
            });
        }
        
        showToast('Role updated successfully', 'success');
        closeModal('editRoleModal');
        loadRoles();
    } catch (error) {
        showToast(`Failed to update role: ${error.message}`, 'error');
    }
}

async function deleteRole(roleName) {
    if (!confirm(`Are you sure you want to delete role "${roleName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/roles/${roleName}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        showToast(result.message, 'success');
        loadRoles();
        loadStats();
    } catch (error) {
        showToast(`Failed to delete role: ${error.message}`, 'error');
    }
}

// ==================== Permission Management ====================

let schemaMetadata = null;

async function loadSchemaMetadata() {
    if (schemaMetadata) return schemaMetadata; // Cache it
    
    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/schema-metadata`);
        schemaMetadata = await response.json();
        return schemaMetadata;
    } catch (error) {
        console.error('Failed to load schema metadata:', error);
        return { node_labels: [], edge_types: [], properties: [] };
    }
}

async function openCreatePermissionModal() {
    document.getElementById('createPermissionForm').reset();
    
    // Load schema metadata and populate datalists
    const schema = await loadSchemaMetadata();
    
    // Populate node labels datalist
    const nodeLabelsDatalist = document.getElementById('nodeLabelsDatalist');
    if (nodeLabelsDatalist) {
        nodeLabelsDatalist.innerHTML = schema.node_labels.map(label => 
            `<option value="${label}">`
        ).join('');
    }
    
    // Populate edge types datalist
    const edgeTypesDatalist = document.getElementById('edgeTypesDatalist');
    if (edgeTypesDatalist) {
        edgeTypesDatalist.innerHTML = schema.edge_types.map(type => 
            `<option value="${type}">`
        ).join('');
    }
    
    // Populate properties datalist
    const propertiesDatalist = document.getElementById('propertiesDatalist');
    if (propertiesDatalist) {
        propertiesDatalist.innerHTML = schema.properties.map(prop => 
            `<option value="${prop}">`
        ).join('');
    }
    
    openModal('createPermissionModal');
}

async function createPermission(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    
    const data = {
        name: formData.get('name'),
        resource: formData.get('resource'),
        action: formData.get('action'),
        description: formData.get('description'),
        grant_type: formData.get('grant_type'),
        node_label: formData.get('node_label') || null,
        edge_type: formData.get('edge_type') || null,
        property_name: formData.get('property_name') || null,
        property_filter: formData.get('property_filter') || null,
        attribute_conditions: formData.get('attribute_conditions') || null
    };

    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/permissions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        showToast(result.message, 'success');
        closeModal('createPermissionModal');
        loadPermissions();
        loadStats();
    } catch (error) {
        showToast(`Failed to create permission: ${error.message}`, 'error');
    }
}

async function openEditPermissionModal(permName) {
    const perm = allPermissions.find(p => p.name === permName);
    if (!perm) return;
    
    // Load schema metadata and populate datalists
    const schema = await loadSchemaMetadata();
    
    // Populate datalists for edit form
    const nodeLabelsDatalist = document.getElementById('editNodeLabelsDatalist');
    if (nodeLabelsDatalist) {
        nodeLabelsDatalist.innerHTML = schema.node_labels.map(label => 
            `<option value="${label}">`
        ).join('');
    }
    
    const edgeTypesDatalist = document.getElementById('editEdgeTypesDatalist');
    if (edgeTypesDatalist) {
        edgeTypesDatalist.innerHTML = schema.edge_types.map(type => 
            `<option value="${type}">`
        ).join('');
    }
    
    const propertiesDatalist = document.getElementById('editPropertiesDatalist');
    if (propertiesDatalist) {
        propertiesDatalist.innerHTML = schema.properties.map(prop => 
            `<option value="${prop}">`
        ).join('');
    }
    
    // Fill form with current values
    document.getElementById('edit_perm_name').value = perm.name;
    document.getElementById('edit_perm_description').value = perm.description || '';
    document.getElementById('edit_perm_grant_type').value = perm.grant_type || 'GRANT';
    document.getElementById('edit_perm_node_label').value = perm.node_label || '';
    document.getElementById('edit_perm_edge_type').value = perm.edge_type || '';
    document.getElementById('edit_perm_property_name').value = perm.property_name || '';
    document.getElementById('edit_perm_property_filter').value = perm.property_filter || '';
    document.getElementById('edit_perm_attribute_conditions').value = perm.attribute_conditions || '';
    
    openModal('editPermissionModal');
}

async function updatePermission(event) {
    event.preventDefault();
    const permName = document.getElementById('edit_perm_name').value;
    
    const data = {
        description: document.getElementById('edit_perm_description').value || null,
        grant_type: document.getElementById('edit_perm_grant_type').value,
        node_label: document.getElementById('edit_perm_node_label').value || null,
        edge_type: document.getElementById('edit_perm_edge_type').value || null,
        property_name: document.getElementById('edit_perm_property_name').value || null,
        property_filter: document.getElementById('edit_perm_property_filter').value || null,
        attribute_conditions: document.getElementById('edit_perm_attribute_conditions').value || null
    };

    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/permissions/${permName}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        showToast(result.message, 'success');
        closeModal('editPermissionModal');
        loadPermissions();
    } catch (error) {
        showToast(`Failed to update permission: ${error.message}`, 'error');
    }
}

async function deletePermission(permName) {
    if (!confirm(`Are you sure you want to delete permission "${permName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await authenticatedFetch(`${API_BASE}/admin/permissions/${permName}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        showToast(result.message, 'success');
        loadPermissions();
        loadStats();
    } catch (error) {
        showToast(`Failed to delete permission: ${error.message}`, 'error');
    }
}
