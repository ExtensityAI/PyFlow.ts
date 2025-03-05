import React, { useState, useEffect } from 'react';
import { UserManager } from './generated/app';

interface User {
  id: string;
  name: string;
  email: string;
}

const UserList: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [newUser, setNewUser] = useState({ id: '', name: '', email: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const userManager = new UserManager();

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const userList = await userManager.list_users();
      setUsers(userList);
      setError(null);
    } catch (err) {
      setError(`Error loading users: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setNewUser({ ...newUser, [name]: value });
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newUser.id || !newUser.name || !newUser.email) {
      setError('All fields are required');
      return;
    }

    try {
      setLoading(true);
      await userManager.add_user(newUser.id, newUser.name, newUser.email);
      setNewUser({ id: '', name: '', email: '' });
      await loadUsers();
      setError(null);
    } catch (err) {
      setError(`Error adding user: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId: string) => {
    try {
      setLoading(true);
      await userManager.delete_user(userId);
      await loadUsers();
      setError(null);
    } catch (err) {
      setError(`Error deleting user: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>User Management</h1>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="user-form">
        <h2>Add New User</h2>
        <form onSubmit={handleAddUser}>
          <div className="form-group">
            <label htmlFor="id">ID:</label>
            <input
              type="text"
              id="id"
              name="id"
              value={newUser.id}
              onChange={handleInputChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="name">Name:</label>
            <input
              type="text"
              id="name"
              name="name"
              value={newUser.name}
              onChange={handleInputChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email:</label>
            <input
              type="email"
              id="email"
              name="email"
              value={newUser.email}
              onChange={handleInputChange}
              required
            />
          </div>

          <button type="submit" disabled={loading}>
            {loading ? 'Adding...' : 'Add User'}
          </button>
        </form>
      </div>

      <div className="user-list">
        <h2>Users</h2>
        {loading && <p>Loading...</p>}

        {!loading && users.length === 0 && (
          <p>No users found.</p>
        )}

        {!loading && users.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id}>
                  <td>{user.id}</td>
                  <td>{user.name}</td>
                  <td>{user.email}</td>
                  <td>
                    <button
                      onClick={() => handleDeleteUser(user.id)}
                      disabled={loading}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default UserList;