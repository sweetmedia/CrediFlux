import Link from 'next/link'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  ArrowRight,
  DollarSign,
  Users,
  TrendingUp,
  Shield,
  CheckCircle2,
  BarChart3,
  Lock,
  Zap,
  Globe,
  HeadphonesIcon
} from 'lucide-react'

export default function Home() {
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b bg-white sticky top-0 z-50 backdrop-blur-sm bg-white/95">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center">
              <Image
                src="/logo.svg"
                alt="CrediFlux"
                width={140}
                height={35}
                className="h-8 w-auto"
                priority
              />
            </Link>
            <nav className="hidden md:flex items-center space-x-8">
              <Link href="#features" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
                Features
              </Link>
              <Link href="#pricing" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
                Pricing
              </Link>
              <Link href="#contact" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
                Contact
              </Link>
            </nav>
            <div className="flex items-center space-x-4">
              <Link href="/login" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
                Sign In
              </Link>
              <Button asChild size="sm" className="bg-indigo-600 hover:bg-indigo-700">
                <Link href="/register">Get Started</Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-indigo-50 via-white to-white">
        <div className="absolute inset-0 bg-grid-gray-900/[0.04] bg-[size:20px_20px]" />
        <div className="container relative mx-auto px-4 lg:px-8 py-20 lg:py-32">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-8 inline-flex items-center rounded-full border border-indigo-200 bg-indigo-50 px-4 py-1.5 text-sm text-indigo-700">
              <Zap className="mr-2 h-4 w-4" />
              <span className="font-medium">Multi-tenant SaaS Platform</span>
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl mb-6">
              Complete Financial Management
              <span className="block bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                for Modern Institutions
              </span>
            </h1>
            <p className="text-lg text-gray-600 mb-10 max-w-2xl mx-auto leading-relaxed">
              Streamline loans, invoicing, accounts receivable, inventory, accounting, and payroll with our powerful all-in-one platform. Built for scale, security, and ease of use.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button size="lg" asChild className="bg-indigo-600 hover:bg-indigo-700 text-base px-8 h-12">
                <Link href="/register">
                  Start Free Trial <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="text-base px-8 h-12">
                <Link href="/dashboard">
                  View Dashboard
                </Link>
              </Button>
            </div>
            <div className="mt-8 flex items-center justify-center gap-8 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                <span>No credit card required</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                <span>14-day free trial</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-20 lg:py-32 bg-white">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-base font-semibold text-indigo-600 mb-3">FEATURES</h2>
            <h3 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
              Everything you need to manage finances
            </h3>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Powerful features designed for financial institutions of all sizes
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature Card 1 */}
            <Card className="border-gray-200 hover:border-indigo-300 transition-colors">
              <CardHeader>
                <div className="h-12 w-12 rounded-lg bg-indigo-100 flex items-center justify-center mb-4">
                  <DollarSign className="h-6 w-6 text-indigo-600" />
                </div>
                <CardTitle className="text-xl">Loan Management</CardTitle>
                <CardDescription className="text-base">
                  Complete loan lifecycle from application to payment tracking
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2.5">
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Customer management</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Automated payment schedules</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Collateral tracking</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Interest calculations</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            {/* Feature Card 2 */}
            <Card className="border-gray-200 hover:border-indigo-300 transition-colors">
              <CardHeader>
                <div className="h-12 w-12 rounded-lg bg-purple-100 flex items-center justify-center mb-4">
                  <Globe className="h-6 w-6 text-purple-600" />
                </div>
                <CardTitle className="text-xl">Multi-Tenant Architecture</CardTitle>
                <CardDescription className="text-base">
                  Secure, isolated data for each organization
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2.5">
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Complete data isolation</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Custom subdomain support</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Role-based access control</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Flexible subscriptions</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            {/* Feature Card 3 */}
            <Card className="border-gray-200 hover:border-indigo-300 transition-colors">
              <CardHeader>
                <div className="h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center mb-4">
                  <BarChart3 className="h-6 w-6 text-blue-600" />
                </div>
                <CardTitle className="text-xl">Advanced Analytics</CardTitle>
                <CardDescription className="text-base">
                  Real-time insights and comprehensive reporting
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2.5">
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Portfolio analytics</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Payment tracking</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Customer metrics</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Export to Excel/PDF</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            {/* Feature Card 4 */}
            <Card className="border-gray-200 hover:border-indigo-300 transition-colors">
              <CardHeader>
                <div className="h-12 w-12 rounded-lg bg-green-100 flex items-center justify-center mb-4">
                  <Lock className="h-6 w-6 text-green-600" />
                </div>
                <CardTitle className="text-xl">Enterprise Security</CardTitle>
                <CardDescription className="text-base">
                  Bank-grade security and compliance
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2.5">
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>JWT authentication</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>256-bit encryption</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Complete audit trails</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>GDPR compliant</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            {/* Feature Card 5 */}
            <Card className="border-gray-200 hover:border-indigo-300 transition-colors">
              <CardHeader>
                <div className="h-12 w-12 rounded-lg bg-orange-100 flex items-center justify-center mb-4">
                  <Users className="h-6 w-6 text-orange-600" />
                </div>
                <CardTitle className="text-xl">Team Collaboration</CardTitle>
                <CardDescription className="text-base">
                  Work together seamlessly across teams
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2.5">
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Unlimited team members</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Custom roles & permissions</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Activity notifications</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Shared workspaces</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            {/* Feature Card 6 */}
            <Card className="border-gray-200 hover:border-indigo-300 transition-colors">
              <CardHeader>
                <div className="h-12 w-12 rounded-lg bg-pink-100 flex items-center justify-center mb-4">
                  <HeadphonesIcon className="h-6 w-6 text-pink-600" />
                </div>
                <CardTitle className="text-xl">24/7 Support</CardTitle>
                <CardDescription className="text-base">
                  Expert support when you need it
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2.5">
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Live chat support</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Email assistance</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Knowledge base</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Video tutorials</span>
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 bg-gradient-to-b from-indigo-600 to-indigo-700 text-white">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-4xl lg:text-5xl font-bold mb-2">500+</div>
              <div className="text-indigo-100 text-lg">Financial Institutions</div>
            </div>
            <div>
              <div className="text-4xl lg:text-5xl font-bold mb-2">$2.5B+</div>
              <div className="text-indigo-100 text-lg">Loans Processed</div>
            </div>
            <div>
              <div className="text-4xl lg:text-5xl font-bold mb-2">99.9%</div>
              <div className="text-indigo-100 text-lg">Uptime SLA</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 lg:py-32 bg-white">
        <div className="container mx-auto px-4 lg:px-8">
          <Card className="border-0 shadow-2xl bg-gradient-to-br from-indigo-600 to-purple-700 text-white overflow-hidden">
            <CardContent className="p-12 lg:p-16 text-center relative">
              <div className="absolute inset-0 bg-grid-white/[0.05] bg-[size:20px_20px]" />
              <div className="relative">
                <h2 className="text-3xl lg:text-4xl font-bold mb-4">
                  Ready to Transform Your Operations?
                </h2>
                <p className="text-xl text-indigo-100 mb-10 max-w-2xl mx-auto">
                  Join hundreds of financial institutions using CrediFlux to streamline their operations
                </p>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <Button size="lg" variant="secondary" asChild className="bg-white text-indigo-600 hover:bg-gray-100 text-base px-8 h-12">
                    <Link href="/register">
                      Start Free Trial <ArrowRight className="ml-2 h-5 w-5" />
                    </Link>
                  </Button>
                  <Button size="lg" variant="outline" asChild className="border-white text-white hover:bg-white/10 text-base px-8 h-12">
                    <Link href="#contact">
                      Contact Sales
                    </Link>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-gray-50">
        <div className="container mx-auto px-4 lg:px-8 py-12">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <Image
                src="/logo.svg"
                alt="CrediFlux"
                width={120}
                height={30}
                className="h-8 w-auto mb-4"
              />
              <p className="text-sm text-gray-600">
                Complete financial management platform for modern institutions.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-4">Product</h3>
              <ul className="space-y-3 text-sm text-gray-600">
                <li><Link href="#features" className="hover:text-gray-900 transition-colors">Features</Link></li>
                <li><Link href="#pricing" className="hover:text-gray-900 transition-colors">Pricing</Link></li>
                <li><Link href="#" className="hover:text-gray-900 transition-colors">Security</Link></li>
                <li><Link href="#" className="hover:text-gray-900 transition-colors">Roadmap</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-4">Company</h3>
              <ul className="space-y-3 text-sm text-gray-600">
                <li><Link href="#" className="hover:text-gray-900 transition-colors">About</Link></li>
                <li><Link href="#" className="hover:text-gray-900 transition-colors">Blog</Link></li>
                <li><Link href="#" className="hover:text-gray-900 transition-colors">Careers</Link></li>
                <li><Link href="#contact" className="hover:text-gray-900 transition-colors">Contact</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-4">Legal</h3>
              <ul className="space-y-3 text-sm text-gray-600">
                <li><Link href="#" className="hover:text-gray-900 transition-colors">Privacy</Link></li>
                <li><Link href="#" className="hover:text-gray-900 transition-colors">Terms</Link></li>
                <li><Link href="#" className="hover:text-gray-900 transition-colors">Cookie Policy</Link></li>
                <li><Link href="#" className="hover:text-gray-900 transition-colors">Licenses</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t pt-8 text-center text-sm text-gray-600">
            <p>&copy; 2025 CrediFlux. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
