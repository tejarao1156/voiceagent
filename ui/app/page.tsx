'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import {
  Phone,
  MessageSquare,
  BarChart3,
  Zap,
  ArrowRight,
  CheckCircle,
  Sparkles,
  Shield,
  Users,
  Clock,
  ChevronRight,
  Sun,
  Moon
} from 'lucide-react'
// import { useTheme } from './components/ThemeProvider'

export default function HomePage() {
  const router = useRouter()
  // const { theme, toggleTheme } = useTheme()

  const features = [
    {
      icon: Phone,
      title: 'AI Voice Agents',
      description: 'Intelligent voice agents that handle customer calls 24/7 with natural, human-like conversations',
      color: 'from-cyan-500 to-blue-600'
    },
    {
      icon: MessageSquare,
      title: 'Smart Messaging',
      description: 'Automated SMS responses powered by AI for instant customer engagement and support',
      color: 'from-purple-500 to-pink-600'
    },
    {
      icon: BarChart3,
      title: 'Analytics Dashboard',
      description: 'Real-time insights into call performance, customer interactions, and agent efficiency',
      color: 'from-orange-500 to-red-600'
    },
    {
      icon: Sparkles,
      title: 'Custom AI Models',
      description: 'Train and customize AI agents to match your brand voice and business needs',
      color: 'from-green-500 to-emerald-600'
    }
  ]

  const stats = [
    { value: '99.9%', label: 'Uptime', icon: Shield },
    { value: '<2s', label: 'Response Time', icon: Clock },
    { value: '10K+', label: 'Active Users', icon: Users },
    { value: '1M+', label: 'Calls Handled', icon: Phone }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-gray-900 dark:via-slate-900 dark:to-gray-900 transition-colors duration-300">
      {/* Navigation */}
      <nav className="relative z-50 border-b border-slate-200/60 dark:border-white/10 bg-white/50 dark:bg-black/20 backdrop-blur-xl transition-colors duration-300">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center space-x-3"
            >
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/50">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <span className="text-2xl font-bold text-slate-900 dark:text-white">
                VoiceAgent
              </span>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center space-x-4"
            >
              {/* Temporarily disabled theme toggle */}
              {/*
              <button 
                onClick={toggleTheme}
                className="p-2 rounded-full bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-white hover:bg-slate-200 dark:hover:bg-white/20 transition-colors"
              >
                {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
              */}
              <button
                onClick={() => window.location.href = '/auth/login'}
                className="px-6 py-2.5 text-slate-600 dark:text-white/80 font-semibold hover:text-slate-900 dark:hover:text-white transition-colors"
              >
                Sign In
              </button>
              <button
                onClick={() => window.location.href = '/auth/signup'}
                className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold shadow-lg shadow-cyan-500/30 hover:shadow-cyan-500/50 transition-all hover:scale-105"
              >
                Get Started Free
              </button>
            </motion.div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 md:py-32">
        {/* Animated Background */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-cyan-500/10 dark:bg-cyan-500/20 blur-3xl" />
          <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-blue-500/10 dark:bg-blue-500/20 blur-3xl" />
          <div className="absolute top-1/2 left-1/2 h-80 w-80 rounded-full bg-purple-500/10 dark:bg-purple-500/20 blur-3xl" />
        </div>

        <div className="container relative z-10 mx-auto px-6">
          <div className="mx-auto max-w-4xl text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className="mb-6 inline-flex items-center space-x-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 backdrop-blur-xl">
                <Sparkles className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
                <span className="text-sm font-semibold text-cyan-700 dark:text-cyan-300">Powered by Advanced AI</span>
              </div>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="mb-6 text-5xl font-black leading-tight text-slate-900 dark:text-white md:text-7xl"
            >
              Transform Customer
              <br />
              <span className="bg-gradient-to-r from-cyan-500 via-blue-600 to-purple-600 dark:from-cyan-400 dark:via-blue-500 dark:to-purple-600 bg-clip-text text-transparent">
                Interactions with AI
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="mb-10 text-xl text-slate-600 dark:text-gray-400 md:text-2xl"
            >
              Build intelligent voice and messaging agents that understand context,
              handle conversations naturally, and scale effortlessly.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-col items-center justify-center space-y-4 sm:flex-row sm:space-x-4 sm:space-y-0"
            >
              <button
                onClick={() => window.location.href = '/auth/signup'}
                className="group flex items-center space-x-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-8 py-4 text-lg font-bold text-white shadow-2xl shadow-cyan-500/40 transition-all hover:scale-105 hover:shadow-cyan-500/60"
              >
                <span>Start Building Free</span>
                <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
              </button>
              
              <button
                onClick={() => window.location.href = '/auth/login'}
                className="flex items-center space-x-2 rounded-lg border border-slate-200 dark:border-white/20 bg-white/50 dark:bg-white/5 px-8 py-4 text-lg font-bold text-slate-700 dark:text-white backdrop-blur-xl transition-all hover:bg-white/80 dark:hover:bg-white/10"
              >
                <span>View Demo</span>
                <ChevronRight className="h-5 w-5" />
              </button>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="relative z-10 border-y border-slate-200/60 dark:border-white/10 bg-white/50 dark:bg-black/20 py-12 backdrop-blur-xl transition-colors duration-300">
        <div className="container mx-auto px-6">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            {stats.map((stat, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.4 + index * 0.1 }}
                className="text-center"
              >
                <stat.icon className="mx-auto mb-3 h-8 w-8 text-cyan-600 dark:text-cyan-400" />
                <div className="mb-1 text-4xl font-black text-slate-900 dark:text-white">{stat.value}</div>
                <div className="text-sm font-medium text-slate-500 dark:text-gray-400">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative z-10 py-20 md:py-32">
        <div className="container mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
            className="mb-16 text-center"
          >
            <h2 className="mb-4 text-4xl font-black text-slate-900 dark:text-white md:text-5xl">
              Everything You Need
            </h2>
            <p className="text-xl text-slate-600 dark:text-gray-400">
              Powerful features to create, manage, and optimize your AI agents
            </p>
          </motion.div>

          <div className="grid gap-8 md:grid-cols-2">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.6 + index * 0.1 }}
                className="group relative overflow-hidden rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-8 backdrop-blur-xl transition-all hover:shadow-2xl dark:hover:bg-white/10"
              >
                <div className={`mb-6 inline-flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br ${feature.color} shadow-lg`}>
                  <feature.icon className="h-7 w-7 text-white" />
                </div>
                
                <h3 className="mb-3 text-2xl font-bold text-slate-900 dark:text-white">
                  {feature.title}
                </h3>
                
                <p className="text-slate-600 dark:text-gray-400">
                  {feature.description}
                </p>

                <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-gradient-to-br opacity-0 blur-2xl transition-opacity group-hover:opacity-10" 
                     style={{ backgroundImage: `linear-gradient(to bottom right, var(--tw-gradient-stops))` }} />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 py-20">
        <div className="container mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 1 }}
            className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-cyan-600 to-blue-700 p-12 text-center shadow-2xl"
          >
            <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48cGF0dGVybiBpZD0iZ3JpZCIgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBwYXR0ZXJuVW5pdHM9InVzZXJTcGFjZU9uVXNlIj48cGF0aCBkPSJNIDQwIDAgTCAwIDAgMCA0MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLW9wYWNpdHk9IjAuMSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-20" />
            
            <div className="relative z-10">
              <h2 className="mb-4 text-4xl font-black text-white md:text-5xl">
                Ready to Get Started?
              </h2>
              
              <p className="mb-8 text-xl text-white/90">
                Join thousands of businesses transforming customer experience with AI
              </p>
              
              <button
                onClick={() => window.location.href = '/auth/signup'}
                className="inline-flex items-center space-x-2 rounded-lg bg-white px-10 py-4 text-lg font-bold text-blue-600 shadow-2xl transition-all hover:scale-105"
              >
                <span>Create Your Free Account</span>
                <ArrowRight className="h-5 w-5" />
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-200/60 dark:border-white/10 bg-white/50 dark:bg-black/20 py-8 backdrop-blur-xl transition-colors duration-300">
        <div className="container mx-auto px-6">
          <p className="text-center text-slate-500 dark:text-gray-500">
            © 2025 VoiceAgent. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}
