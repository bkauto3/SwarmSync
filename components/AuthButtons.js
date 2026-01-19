import { useAuth, loginWithGoogle, loginWithGithub, logout } from '../lib/auth';

export default function AuthButtons() {
  const { authenticated, session } = useAuth();

  if (authenticated) {
    return (
      <div className="flex items-center space-x-4">
        <span className="text-sm">Welcome, {session.user.name || session.user.email}</span>
        <button
          onClick={logout}
          className="px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300 transition-colors"
        >
          Logout
        </button>
      </div>
    );
  }

  return (
    <div className="flex space-x-4">
      <button
        onClick={loginWithGoogle}
        className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors"
      >
        Login with Google
      </button>
      <button
        onClick={loginWithGithub}
        className="px-4 py-2 bg-gray-800 text-white rounded-md hover:bg-gray-900 transition-colors"
      >
        Login with GitHub
      </button>
    </div>
  );
}
