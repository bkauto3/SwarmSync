import { signIn, signOut, useSession } from "next-auth/react";

export const useAuth = () => {
  const { data: session, status } = useSession();
  
  return {
    session,
    loading: status === "loading",
    authenticated: !!session,
  };
};

export const loginWithGoogle = () => {
  signIn("google", { 
    callbackUrl: ${window.location.origin}/dashboard,
  });
};

export const loginWithGithub = () => {
  signIn("github", { 
    callbackUrl: ${window.location.origin}/dashboard,
  });
};

export const logout = () => {
  signOut({ callbackUrl: ${window.location.origin}/ });
};
