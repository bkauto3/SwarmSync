import { useRouter } from 'next/router';
import Link from 'next/link';

export default function AuthError() {
  const router = useRouter();
  const { error } = router.query;

  const errorMessages = {
    'OAuthAccountNotLinked': 'This email is already associated with another account. Please sign in with the provider you used originally.',
    'OAuthCallback': 'There was an error during the authentication process. Please try again.',
    'OAuthSignin': 'There was an error signing in with the provider. Please try again.',
    'EmailCreateAccount': 'Unable to create account with email. Please try a different method.',
    'Callback': 'There was an error during the authentication callback. Please try again.',
    'OAuthProfile': 'Unable to fetch profile information from the provider. Please try again.',
    'default': 'An unexpected error occurred during authentication. Please try again.'
  };

  const errorMessage = errorMessages[error] || errorMessages.default;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Authentication Error
          </h2>
        </div>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{errorMessage}</span>
        </div>
        <div className="flex flex-col space-y-4">
          <Link href="/auth/signin">
            <button className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
              Try Again
            </button>
          </Link>
          <Link href="/">
            <button className="group relative w-full flex justify-center py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
              Go Home
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}
