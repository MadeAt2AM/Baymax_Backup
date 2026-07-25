import { useCallback } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../lib/auth-context";

import styles from "../lib/styles.module.css";

interface HeaderProps {
  username: string;
}

export function Header({ username }: HeaderProps) {
  const { signOut } = useAuth();
  // signOut flips the AuthContext state to "anonymous", so the App's
  // router automatically swaps the gated branch for the login page.
  // No navigate() call needed.
  const handleLogout = useCallback(async () => {
    await signOut();
  }, [signOut]);

  return (
    <header className={styles.appHeader}>
      <h1>Competitors Intelligence</h1>
      <nav>
        <Link to="/">Dashboard</Link>
        <Link to="/reels">Reels</Link>
        <Link to="/runs">Runs</Link>
      </nav>
      <div>
        <span style={{ marginRight: 12, fontSize: 13 }}>{username}</span>
        <button type="button" onClick={handleLogout}>
          Log out
        </button>
      </div>
    </header>
  );
}
