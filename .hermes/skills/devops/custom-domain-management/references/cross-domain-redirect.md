# Cross-Domain Redirect Pattern

When a user belongs to a tenant with a verified custom domain, SYNTRA automatically redirects them to their company's branded domain after login.

## Backend Change

Add `companyDomain` to the login response (`/api/auth/login` and `/api/auth/me`):

```typescript
// auth.ts
let companyDomain: string | null = null;
if (user.companyId) {
  const [company] = await db
    .select({ customDomain: companies.customDomain, domainStatus: companies.domainStatus })
    .from(companies)
    .where(eq(companies.id, user.companyId))
    .limit(1);
  if (company?.customDomain && company.domainStatus === 'verified') {
    companyDomain = company.customDomain;
  }
}
res.json({ ...user, companyDomain });
```

## Frontend Logic

### Login Page (`login.tsx`)

```typescript
onSuccess: (response) => {
  const mustChange = (response as any).user?.mustChangePassword ?? false;
  const role = (response as any).user?.role;
  const companyDomain = (response as any).companyDomain as string | null | undefined;
  login(response.token, mustChange);

  let localDest = '/dashboard';
  if (mustChange) localDest = '/change-password';
  else if (role === 'platform_admin') localDest = '/platform';

  // Auto-redirect for tenant users (skip platform_admin + mustChange)
  if (!mustChange && role !== 'platform_admin' && companyDomain && companyDomain !== window.location.hostname) {
    window.location.href = `https://${companyDomain}${localDest}`;
    return;
  }
  setLocation(localDest);
},
```

### Auth Hook (`use-auth.tsx`)

Add a wrong-host check on page reload:

```typescript
useEffect(() => {
  if (!user || isLoading) return;
  if (user.role === 'platform_admin') return;
  const companyDomain = (user as any).companyDomain as string | null | undefined;
  if (!companyDomain) return;
  if (companyDomain === window.location.hostname) return;
  window.location.href = `https://${companyDomain}${window.location.pathname}${window.location.search}`;
}, [user, isLoading]);
```

### Branding-Aware "Back" Link

Hide the "Back to SYNTRA home" link on branded pages:

```tsx
{!branding?.branded && (
  <Link href="/">...</Link>
)}
```

This prevents customers from clicking through to the SYNTRA marketing page when they
should be staying within their white-label experience.