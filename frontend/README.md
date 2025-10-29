# CrediFlux Frontend

Frontend application built with Next.js 14+, TypeScript, and shadcn/ui for the CrediFlux multi-module SaaS platform.

## Tech Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (Radix UI)
- **Forms**: React Hook Form + Zod
- **HTTP Client**: Axios
- **State Management**: TanStack Query (React Query)
- **Tables**: TanStack Table
- **Charts**: Recharts
- **Icons**: Lucide React

## Project Structure

```
frontend/
├── app/                      # Next.js app directory
│   ├── (auth)/              # Auth routes (login, register)
│   ├── dashboard/           # Dashboard page
│   ├── loans/               # Loans module pages
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Home page
│   └── globals.css          # Global styles
├── components/              # React components
│   ├── ui/                  # shadcn/ui components
│   ├── layout/              # Layout components
│   └── loans/               # Loan-specific components
├── lib/                     # Utilities and configurations
│   ├── api/                 # API clients
│   │   ├── client.ts        # Axios client with interceptors
│   │   ├── auth.ts          # Auth API
│   │   ├── loans.ts         # Loans API
│   │   └── customers.ts     # Customers API
│   ├── auth/                # Auth utilities
│   └── utils.ts             # General utilities
├── hooks/                   # Custom React hooks
├── types/                   # TypeScript type definitions
│   └── index.ts             # All type definitions
└── public/                  # Static assets
```

## Getting Started

### Prerequisites

- Node.js 18+ (preferably 20+)
- npm or yarn
- Backend API running on http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# or
yarn install
```

### Environment Variables

Create a `.env.local` file in the root directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=CrediFlux
```

### Development

```bash
# Run development server
npm run dev

# or
yarn dev
```

The application will be available at [http://localhost:3000](http://localhost:3000)

### Building for Production

```bash
# Build the application
npm run build

# Start production server
npm run start
```

### Linting

```bash
npm run lint
```

## API Integration

### Authentication

The application uses JWT tokens for authentication. Tokens are automatically managed by the API client:

```typescript
import { authAPI } from '@/lib/api/auth';

// Login
const response = await authAPI.login({
  email: 'user@example.com',
  password: 'password'
});
// Tokens are automatically stored in localStorage

// Get current user
const user = await authAPI.getCurrentUser();

// Logout
await authAPI.logout();
```

### Making API Calls

All API calls use the centralized API client with automatic token refresh:

```typescript
import { loansAPI } from '@/lib/api/loans';

// Get all loans
const loans = await loansAPI.getLoans({
  page: 1,
  search: 'John',
  status: 'active'
});

// Get specific loan
const loan = await loansAPI.getLoan('loan-id');

// Create loan
const newLoan = await loansAPI.createLoan({
  customer: 'customer-id',
  loan_type: 'personal',
  principal_amount: 50000,
  // ...other fields
});

// Approve loan
await loansAPI.approveLoan('loan-id');
```

## Components

### UI Components (shadcn/ui)

Basic UI components are available in `components/ui/`:

- **Button**: Primary UI button component
- **Card**: Card container with header, content, footer
- **Input**: Form input field
- **Label**: Form label
- More components can be added using `npx shadcn-ui add`

### Using Components

```tsx
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

export default function MyComponent() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Card Title</CardTitle>
      </CardHeader>
      <CardContent>
        <p>Card content goes here</p>
        <Button onClick={() => console.log('Clicked')}>
          Click Me
        </Button>
      </CardContent>
    </Card>
  );
}
```

## Type Safety

All API responses are fully typed. Types are defined in `types/index.ts`:

```typescript
import { Loan, Customer, LoanPayment } from '@/types';

// TypeScript will provide autocomplete and type checking
const loan: Loan = await loansAPI.getLoan('id');
console.log(loan.customer_name); // ✅ Type-safe
console.log(loan.invalidField); // ❌ TypeScript error
```

## Styling

### Tailwind CSS

The project uses Tailwind CSS for styling. The configuration supports:

- CSS variables for theming
- Dark mode support (via `dark` class)
- Custom color palette
- Responsive design utilities

### Custom Colors

Colors are defined using CSS variables in `app/globals.css` and can be used in Tailwind:

```tsx
<div className="bg-primary text-primary-foreground">
  Primary colored div
</div>

<div className="bg-secondary text-secondary-foreground">
  Secondary colored div
</div>

<div className="bg-destructive text-destructive-foreground">
  Error/destructive styled div
</div>
```

## Utilities

### Formatting Utilities

```typescript
import { formatCurrency, formatDate, formatDateTime } from '@/lib/utils';

formatCurrency(50000, 'USD'); // "$50,000.00"
formatDate('2025-01-15'); // "January 15, 2025"
formatDateTime('2025-01-15T14:30:00'); // "Jan 15, 2025, 2:30 PM"
```

### Class Name Utility

```typescript
import { cn } from '@/lib/utils';

// Merge Tailwind classes intelligently
const className = cn(
  'base-class',
  condition && 'conditional-class',
  'another-class'
);
```

## Pages

### Home Page (`/`)
- Landing page with features overview
- Call-to-action sections
- Navigation to login/register

### Dashboard (`/dashboard`)
- Overview statistics
- Recent loans and payments
- Quick actions
- Navigation to all modules

### Loans Module (`/loans`)
- Loan list with filters and search
- Loan details view
- Create/edit loan forms
- Payment management
- Schedule viewing

### Customers (`/loans/customers`)
- Customer list with search
- Customer profiles
- Loan history per customer
- Customer statistics

## Adding New Pages

1. Create a new folder in `app/` directory
2. Add a `page.tsx` file
3. Export a default component

```tsx
// app/my-page/page.tsx
export default function MyPage() {
  return (
    <div>
      <h1>My Page</h1>
    </div>
  );
}
```

The page will automatically be available at `/my-page`.

## Adding shadcn/ui Components

You can add more shadcn/ui components using the CLI:

```bash
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add form
npx shadcn-ui@latest add table
npx shadcn-ui@latest add select
npx shadcn-ui@latest add calendar
```

## Best Practices

1. **Use TypeScript**: Always type your props and state
2. **Use API utilities**: Don't call axios directly, use the API utilities in `lib/api/`
3. **Use shadcn/ui components**: Build on top of the existing UI components
4. **Follow the folder structure**: Keep components organized
5. **Use server components**: Make components server components by default, only use 'use client' when necessary
6. **Handle errors**: Always handle API errors appropriately
7. **Use loading states**: Provide feedback during async operations

## Troubleshooting

### Port Already in Use

If port 3000 is already in use:

```bash
# Find and kill the process
lsof -ti:3000 | xargs kill -9

# Or use a different port
PORT=3001 npm run dev
```

### API Connection Issues

Make sure:
1. Backend is running on http://localhost:8000
2. CORS is properly configured in backend
3. `.env.local` has correct `NEXT_PUBLIC_API_URL`

### TypeScript Errors

```bash
# Restart TypeScript server in VS Code
Cmd/Ctrl + Shift + P -> "TypeScript: Restart TS Server"

# Check for type errors
npm run build
```

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Test thoroughly
4. Create a pull request

## License

Proprietary - All rights reserved
