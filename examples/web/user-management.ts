import { UserManager } from './generated/app';

async function manageUsers() {
  const userManager = new UserManager();

  console.log("Adding users...");
  await userManager.add_user("user1", "John Doe", "john@example.com");
  await userManager.add_user("user2", "Jane Smith", "jane@example.com");
  await userManager.add_user("user3", "Bob Johnson", "bob@example.com");

  console.log("\nListing all users:");
  const users = await userManager.list_users();
  users.forEach(user => {
    console.log(`- ${user.id}: ${user.name} (${user.email})`);
  });

  console.log("\nGetting a single user:");
  const user2 = await userManager.get_user("user2");
  console.log(`User: ${user2.name} (${user2.email})`);

  console.log("\nUpdating a user:");
  const updatedUser = await userManager.update_user("user1", "John Updated", "john.updated@example.com");
  console.log(`Updated user: ${updatedUser.name} (${updatedUser.email})`);

  console.log("\nDeleting a user:");
  await userManager.delete_user("user3");

  console.log("\nFinal user list:");
  const finalUsers = await userManager.list_users();
  finalUsers.forEach(user => {
    console.log(`- ${user.id}: ${user.name} (${user.email})`);
  });
}

manageUsers().catch(console.error);
