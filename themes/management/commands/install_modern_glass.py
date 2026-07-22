"""
themes/management/commands/install_modern_glass.py

One-shot command that creates, extracts, and registers the
Modern Glass theme into the database and marks it APPROVED.

Usage:
    py manage.py install_modern_glass
    py manage.py install_modern_glass --force   (re-install even if already exists)
"""

import io
import json
import os
import zipfile
import shutil
import textwrap

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

# ── HTML CONTENT ───────────────────────────────────────────────────────────────
# The complete single-file Modern Glass portfolio theme.
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{{ personal.tagline }}">
    <meta name="keywords" content="{{ personal.title }}, portfolio, developer">
    <meta name="author" content="{{ personal.name }}">
    <meta property="og:title" content="{{ personal.name }} — {{ personal.title }}">
    <meta property="og:description" content="{{ personal.tagline }}">
    <meta property="og:image" content="{{ personal.photo }}">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{{ personal.name }} — {{ personal.title }}">
    <meta name="twitter:description" content="{{ personal.tagline }}">
    <title id="page-title">{{ personal.name }} — {{ personal.title }}</title>

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">

    <style>
        :root {
            --accent:#6c63ff; --accent2:#00d4aa; --accent3:#ff6b6b;
            --glass-bg:rgba(255,255,255,.06); --glass-border:rgba(255,255,255,.12);
            --glass-shadow:0 8px 32px rgba(0,0,0,.4);
            --text-primary:#f0f4ff; --text-secondary:#a8b2d8; --text-muted:#6b7a9e;
            --bg-dark:#080c1a; --transition:all .35s cubic-bezier(.4,0,.2,1);
        }
        [data-theme="light"] {
            --glass-bg:rgba(255,255,255,.70); --glass-border:rgba(108,99,255,.15);
            --glass-shadow:0 8px 32px rgba(108,99,255,.12);
            --text-primary:#0f1629; --text-secondary:#3d4a6e; --text-muted:#7a88ab;
            --bg-dark:#f0f4ff;
        }
        *{box-sizing:border-box;margin:0;padding:0}
        html{scroll-behavior:smooth}
        body{
            font-family:'Inter',sans-serif;
            background:var(--bg-dark);
            color:var(--text-primary);
            overflow-x:hidden;
            transition:var(--transition);
        }

        /* ── BACKGROUND ── */
        .bg-wrap{position:fixed;inset:0;z-index:-1;overflow:hidden}
        [data-theme="dark"] .bg-wrap{
            background:radial-gradient(ellipse at 20% 50%,rgba(108,99,255,.15) 0%,transparent 50%),
                        radial-gradient(ellipse at 80% 20%,rgba(0,212,170,.10) 0%,transparent 50%),
                        linear-gradient(135deg,#080c1a 0%,#0f1629 100%);
        }
        [data-theme="light"] .bg-wrap{
            background:radial-gradient(ellipse at 20% 50%,rgba(108,99,255,.07) 0%,transparent 50%),
                        radial-gradient(ellipse at 80% 20%,rgba(0,212,170,.05) 0%,transparent 50%),
                        linear-gradient(135deg,#f0f4ff 0%,#e8edff 100%);
        }
        .blob{position:absolute;border-radius:50%;filter:blur(90px);animation:blobFloat 9s ease-in-out infinite;opacity:.45}
        .blob-1{width:550px;height:550px;background:rgba(108,99,255,.18);top:-120px;left:-120px;animation-delay:0s}
        .blob-2{width:450px;height:450px;background:rgba(0,212,170,.12);bottom:-120px;right:-60px;animation-delay:3s}
        .blob-3{width:350px;height:350px;background:rgba(255,107,107,.09);top:50%;left:50%;animation-delay:6s}
        @keyframes blobFloat{0%,100%{transform:translate(0,0) scale(1)}33%{transform:translate(30px,-30px) scale(1.05)}66%{transform:translate(-20px,20px) scale(.95)}}

        /* ── LOADER ── */
        #loader{position:fixed;inset:0;background:#080c1a;z-index:9999;display:flex;align-items:center;justify-content:center;transition:opacity .6s,visibility .6s}
        #loader.hidden{opacity:0;visibility:hidden;pointer-events:none}
        .loader-ring{width:56px;height:56px;border:3px solid rgba(108,99,255,.2);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}
        @keyframes spin{to{transform:rotate(360deg)}}

        /* ── GLASS CARD ── */
        .glass-card{
            background:var(--glass-bg);
            border:1px solid var(--glass-border);
            border-radius:20px;
            backdrop-filter:blur(20px);
            -webkit-backdrop-filter:blur(20px);
            box-shadow:var(--glass-shadow);
            transition:var(--transition);
        }
        .glass-card:hover{transform:translateY(-4px);box-shadow:0 20px 60px rgba(108,99,255,.18);border-color:rgba(108,99,255,.3)}

        /* ── BUTTONS ── */
        .btn-grd{
            background:linear-gradient(135deg,var(--accent) 0%,#8b5cf6 100%);
            border:none;color:#fff;padding:12px 32px;border-radius:50px;
            font-weight:600;font-size:.9rem;letter-spacing:.5px;
            transition:var(--transition);cursor:pointer;display:inline-flex;align-items:center;gap:8px;
            text-decoration:none;
        }
        .btn-grd:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(108,99,255,.4);color:#fff}
        .btn-outline-gl{
            background:transparent;border:1px solid var(--glass-border);
            color:var(--text-primary);padding:12px 32px;border-radius:50px;
            font-weight:500;transition:var(--transition);cursor:pointer;
            display:inline-flex;align-items:center;gap:8px;text-decoration:none;
        }
        .btn-outline-gl:hover{background:var(--glass-bg);border-color:var(--accent);color:var(--accent);transform:translateY(-2px)}

        /* ── NAVBAR ── */
        #mainNav{
            position:fixed;top:0;left:0;right:0;z-index:1000;
            padding:18px 0;transition:var(--transition);
        }
        #mainNav.scrolled{
            background:rgba(8,12,26,.85);backdrop-filter:blur(20px);
            -webkit-backdrop-filter:blur(20px);padding:10px 0;
            border-bottom:1px solid var(--glass-border);
        }
        [data-theme="light"] #mainNav.scrolled{background:rgba(240,244,255,.90)}
        .nav-brand{
            font-family:'Space Grotesk',sans-serif;font-size:1.4rem;font-weight:700;
            background:linear-gradient(135deg,var(--accent),var(--accent2));
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
            text-decoration:none;
        }
        .nav-link-custom{
            color:var(--text-secondary)!important;font-weight:500;font-size:.875rem;
            padding:6px 14px!important;border-radius:8px;transition:var(--transition);position:relative;
        }
        .nav-link-custom::after{
            content:'';position:absolute;bottom:0;left:14px;right:14px;height:2px;
            background:linear-gradient(90deg,var(--accent),var(--accent2));
            transform:scaleX(0);transition:transform .3s ease;border-radius:2px;
        }
        .nav-link-custom:hover,.nav-link-custom.active{color:var(--text-primary)!important}
        .nav-link-custom:hover::after,.nav-link-custom.active::after{transform:scaleX(1)}
        .theme-btn{
            width:38px;height:38px;border-radius:50%;border:1px solid var(--glass-border);
            background:var(--glass-bg);color:var(--text-primary);
            display:flex;align-items:center;justify-content:center;
            cursor:pointer;transition:var(--transition);backdrop-filter:blur(10px);
        }
        .theme-btn:hover{border-color:var(--accent);color:var(--accent);transform:rotate(20deg)}

        /* ── HERO ── */
        #hero{min-height:100vh;display:flex;align-items:center;padding:120px 0 80px}
        .hero-badge{
            display:inline-flex;align-items:center;gap:8px;
            background:var(--glass-bg);border:1px solid var(--glass-border);
            border-radius:50px;padding:8px 20px;font-size:.78rem;
            color:var(--accent2);font-weight:600;letter-spacing:.5px;
            backdrop-filter:blur(10px);margin-bottom:24px;
        }
        .dot{width:8px;height:8px;background:var(--accent2);border-radius:50%;animation:pulse 2s ease-in-out infinite}
        @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(1.3)}}
        .hero-name{
            font-family:'Space Grotesk',sans-serif;
            font-size:clamp(2.5rem,6vw,5rem);font-weight:800;line-height:1.1;
            background:linear-gradient(135deg,#fff 0%,rgba(255,255,255,.8) 40%,var(--accent) 100%);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
            margin-bottom:12px;
        }
        [data-theme="light"] .hero-name{background:linear-gradient(135deg,#0f1629 0%,var(--accent) 100%);-webkit-background-clip:text;background-clip:text}
        .hero-title{font-size:clamp(1rem,2.5vw,1.4rem);color:var(--accent2);font-weight:600;margin-bottom:20px}
        .hero-tagline{font-size:1rem;color:var(--text-secondary);line-height:1.7;max-width:520px;margin-bottom:40px}

        .hero-photo-wrap{position:relative;display:inline-block}
        .hero-photo-wrap::before{
            content:'';position:absolute;inset:-3px;border-radius:50%;
            background:linear-gradient(135deg,var(--accent),var(--accent2),var(--accent3));
            z-index:-1;animation:rotateBorder 4s linear infinite;
        }
        @keyframes rotateBorder{to{transform:rotate(360deg)}}
        .hero-photo{width:280px;height:280px;border-radius:50%;object-fit:cover;border:4px solid var(--bg-dark);display:block}
        .hero-avatar{
            width:280px;height:280px;border-radius:50%;
            background:linear-gradient(135deg,var(--accent),var(--accent2));
            display:flex;align-items:center;justify-content:center;
            font-size:6rem;color:rgba(255,255,255,.9);
            font-family:'Space Grotesk',sans-serif;font-weight:700;
            border:4px solid var(--bg-dark);
        }
        .stat-card{text-align:center;padding:16px 10px}
        .stat-num{
            font-family:'Space Grotesk',sans-serif;font-size:1.8rem;font-weight:800;
            background:linear-gradient(135deg,var(--accent),var(--accent2));
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
        }
        .stat-label{font-size:.75rem;color:var(--text-muted);font-weight:500;letter-spacing:.5px}
        .social-links a{
            width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center;
            border-radius:12px;background:var(--glass-bg);border:1px solid var(--glass-border);
            color:var(--text-secondary);font-size:1.1rem;text-decoration:none;transition:var(--transition);
            backdrop-filter:blur(10px);
        }
        .social-links a:hover{background:var(--accent);border-color:var(--accent);color:#fff;transform:translateY(-3px);box-shadow:0 8px 20px rgba(108,99,255,.4)}

        /* ── SECTIONS ── */
        section{padding:100px 0}
        .section-badge{
            display:inline-flex;align-items:center;gap:8px;
            font-size:.72rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--accent);margin-bottom:16px;
        }
        .section-badge::before{content:'';width:24px;height:2px;background:var(--accent);border-radius:2px}
        .section-title{
            font-family:'Space Grotesk',sans-serif;font-size:clamp(2rem,4vw,2.8rem);
            font-weight:800;color:var(--text-primary);line-height:1.2;margin-bottom:14px;
        }
        .section-sub{font-size:1rem;color:var(--text-secondary);max-width:540px;line-height:1.7}

        /* ── ABOUT ── */
        .about-photo{width:100%;max-width:400px;border-radius:24px;object-fit:cover;aspect-ratio:4/5}
        .about-fallback{
            width:100%;max-width:400px;aspect-ratio:4/5;border-radius:24px;
            background:linear-gradient(135deg,var(--accent),var(--accent2));
            display:flex;align-items:center;justify-content:center;font-size:8rem;
            color:rgba(255,255,255,.35);
        }
        .info-row{
            display:flex;align-items:center;gap:14px;
            background:var(--glass-bg);border:1px solid var(--glass-border);
            border-radius:14px;padding:14px 18px;margin-bottom:10px;
            backdrop-filter:blur(10px);
        }
        .info-row i{color:var(--accent);font-size:1.1rem;flex-shrink:0}
        .info-lbl{font-size:.72rem;color:var(--text-muted);font-weight:600;letter-spacing:.5px;text-transform:uppercase}
        .info-val{font-size:.9rem;color:var(--text-primary);font-weight:600}

        /* ── SKILLS ── */
        .skill-tag{
            display:inline-flex;align-items:center;gap:5px;
            padding:7px 16px;border-radius:50px;font-size:.83rem;font-weight:600;
            border:1px solid transparent;transition:var(--transition);cursor:default;
        }
        .skill-tag:hover{transform:translateY(-3px) scale(1.05);box-shadow:0 4px 15px rgba(0,0,0,.2)}
        .sk-tech{background:rgba(108,99,255,.12);border-color:rgba(108,99,255,.3);color:#a78bfa}
        .sk-soft{background:rgba(0,212,170,.12);border-color:rgba(0,212,170,.3);color:#34d399}
        .sk-lang{background:rgba(251,191,36,.12);border-color:rgba(251,191,36,.3);color:#fbbf24}
        .sk-fw{background:rgba(239,68,68,.12);border-color:rgba(239,68,68,.3);color:#f87171}
        .sk-tool{background:rgba(14,165,233,.12);border-color:rgba(14,165,233,.3);color:#38bdf8}
        .skill-cat{font-size:.72rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--text-muted);margin-bottom:14px}

        /* ── TIMELINE ── */
        .timeline{position:relative;padding-left:32px}
        .timeline::before{
            content:'';position:absolute;left:8px;top:0;bottom:0;
            width:2px;background:linear-gradient(to bottom,var(--accent),var(--accent2),transparent);
            border-radius:2px;
        }
        .tl-item{position:relative;margin-bottom:36px;opacity:0;transform:translateX(-20px);transition:all .6s ease}
        .tl-item.visible{opacity:1;transform:translateX(0)}
        .tl-dot{
            position:absolute;left:-28px;top:6px;width:14px;height:14px;
            border-radius:50%;background:var(--accent);border:3px solid var(--bg-dark);
            box-shadow:0 0 0 2px var(--accent);
        }
        .tl-card{
            background:var(--glass-bg);border:1px solid var(--glass-border);
            border-radius:16px;padding:22px;backdrop-filter:blur(20px);transition:var(--transition);
        }
        .tl-card:hover{border-color:rgba(108,99,255,.4);box-shadow:0 8px 30px rgba(108,99,255,.15)}
        .tl-period{
            display:inline-flex;align-items:center;gap:6px;font-size:.76rem;
            color:var(--accent2);font-weight:600;background:rgba(0,212,170,.1);
            border:1px solid rgba(0,212,170,.2);border-radius:50px;padding:3px 13px;margin-bottom:10px;
        }
        .tl-role{font-family:'Space Grotesk',sans-serif;font-size:1.05rem;font-weight:700;color:var(--text-primary);margin-bottom:3px}
        .tl-org{font-size:.88rem;color:var(--accent);font-weight:600;margin-bottom:8px}
        .tl-desc{font-size:.85rem;color:var(--text-secondary);line-height:1.7}

        /* ── PROJECTS ── */
        .filter-bar{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:36px;justify-content:center}
        .filter-btn{
            padding:8px 22px;border-radius:50px;border:1px solid var(--glass-border);
            background:var(--glass-bg);color:var(--text-secondary);font-size:.84rem;
            font-weight:600;cursor:pointer;transition:var(--transition);backdrop-filter:blur(10px);
        }
        .filter-btn.active,.filter-btn:hover{background:var(--accent);border-color:var(--accent);color:#fff}
        .proj-card{
            background:var(--glass-bg);border:1px solid var(--glass-border);
            border-radius:20px;overflow:hidden;backdrop-filter:blur(20px);
            transition:var(--transition);height:100%;
        }
        .proj-card:hover{transform:translateY(-8px);box-shadow:0 20px 60px rgba(108,99,255,.2);border-color:rgba(108,99,255,.4)}
        .proj-img-wrap{position:relative;aspect-ratio:16/9;overflow:hidden;background:linear-gradient(135deg,rgba(108,99,255,.2),rgba(0,212,170,.1))}
        .proj-img-wrap img{width:100%;height:100%;object-fit:cover;transition:transform .5s ease}
        .proj-card:hover .proj-img-wrap img{transform:scale(1.08)}
        .proj-placeholder{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:3rem;color:rgba(108,99,255,.4)}
        .proj-overlay{
            position:absolute;inset:0;
            background:linear-gradient(to top,rgba(15,22,41,.9) 0%,transparent 60%);
            opacity:0;transition:var(--transition);display:flex;align-items:flex-end;padding:16px;gap:8px;
        }
        .proj-card:hover .proj-overlay{opacity:1}
        .proj-overlay a{
            display:inline-flex;align-items:center;gap:5px;color:#fff;
            background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);
            border-radius:8px;padding:7px 14px;font-size:.78rem;font-weight:600;
            text-decoration:none;backdrop-filter:blur(10px);transition:var(--transition);
        }
        .proj-overlay a:hover{background:var(--accent);border-color:var(--accent)}
        .proj-body{padding:22px}
        .proj-tags{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:12px}
        .proj-tag{
            font-size:.7rem;font-weight:700;padding:3px 10px;border-radius:50px;
            background:rgba(108,99,255,.15);border:1px solid rgba(108,99,255,.25);color:#a78bfa;
        }
        .proj-title{font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:700;color:var(--text-primary);margin-bottom:6px}
        .proj-desc{font-size:.84rem;color:var(--text-secondary);line-height:1.65}

        /* ── SERVICES ── */
        .svc-card{padding:36px 26px;text-align:center}
        .svc-icon{
            width:68px;height:68px;border-radius:20px;margin:0 auto 22px;
            background:linear-gradient(135deg,rgba(108,99,255,.2),rgba(0,212,170,.1));
            border:1px solid rgba(108,99,255,.3);display:flex;align-items:center;justify-content:center;
            font-size:1.75rem;color:var(--accent);transition:var(--transition);
        }
        .svc-card:hover .svc-icon{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;transform:rotateY(180deg)}
        .svc-title{font-family:'Space Grotesk',sans-serif;font-size:1.05rem;font-weight:700;color:var(--text-primary);margin-bottom:10px}
        .svc-desc{font-size:.86rem;color:var(--text-secondary);line-height:1.7}

        /* ── CERTIFICATES ── */
        .cert-card{display:flex;gap:18px;align-items:flex-start;padding:22px}
        .cert-icon{
            width:50px;height:50px;border-radius:14px;flex-shrink:0;
            background:linear-gradient(135deg,var(--accent),var(--accent2));
            display:flex;align-items:center;justify-content:center;font-size:1.25rem;color:#fff;
        }
        .cert-name{font-weight:700;color:var(--text-primary);margin-bottom:3px}
        .cert-issuer{font-size:.83rem;color:var(--accent2);font-weight:600}
        .cert-year{font-size:.78rem;color:var(--text-muted);margin-top:4px}

        /* ── ACHIEVEMENTS ── */
        .ach-card{display:flex;gap:18px;align-items:flex-start;padding:22px}
        .ach-icon{
            width:50px;height:50px;border-radius:14px;flex-shrink:0;
            background:linear-gradient(135deg,#f59e0b,#ef4444);
            display:flex;align-items:center;justify-content:center;font-size:1.25rem;color:#fff;
        }
        .ach-title{font-weight:700;color:var(--text-primary);margin-bottom:3px}
        .ach-desc{font-size:.84rem;color:var(--text-secondary);line-height:1.6}

        /* ── CONTACT ── */
        .contact-info{display:flex;align-items:center;gap:16px;padding:18px 22px;margin-bottom:14px}
        .contact-icon{
            width:48px;height:48px;border-radius:14px;flex-shrink:0;
            background:linear-gradient(135deg,rgba(108,99,255,.2),rgba(0,212,170,.1));
            border:1px solid rgba(108,99,255,.3);display:flex;align-items:center;justify-content:center;
            font-size:1.15rem;color:var(--accent);
        }
        .contact-lbl{font-size:.72rem;color:var(--text-muted);font-weight:600;letter-spacing:.5px;text-transform:uppercase}
        .contact-val{font-size:.9rem;color:var(--text-primary);font-weight:600}
        .form-gl{
            background:var(--glass-bg)!important;border:1px solid var(--glass-border)!important;
            border-radius:12px!important;color:var(--text-primary)!important;
            padding:13px 17px!important;font-size:.9rem!important;
            backdrop-filter:blur(10px);transition:var(--transition)!important;
        }
        .form-gl::placeholder{color:var(--text-muted)!important}
        .form-gl:focus{box-shadow:0 0 0 3px rgba(108,99,255,.15)!important;border-color:var(--accent)!important;outline:none!important}
        .form-label-gl{color:var(--text-secondary);font-size:.82rem;font-weight:600;margin-bottom:6px;display:block}

        /* ── FOOTER ── */
        footer{padding:56px 0 28px;border-top:1px solid var(--glass-border)}
        .footer-brand{
            font-family:'Space Grotesk',sans-serif;font-size:1.35rem;font-weight:700;
            background:linear-gradient(135deg,var(--accent),var(--accent2));
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
        }
        .footer-copy{font-size:.83rem;color:var(--text-muted)}

        /* ── BACK TO TOP ── */
        #btt{
            position:fixed;bottom:28px;right:28px;width:46px;height:46px;border-radius:50%;
            background:linear-gradient(135deg,var(--accent),var(--accent2));
            color:#fff;border:none;display:flex;align-items:center;justify-content:center;
            font-size:1.1rem;cursor:pointer;z-index:999;
            opacity:0;visibility:hidden;transform:translateY(20px);transition:var(--transition);
            box-shadow:0 4px 20px rgba(108,99,255,.4);
        }
        #btt.visible{opacity:1;visibility:visible;transform:translateY(0)}
        #btt:hover{transform:translateY(-4px);box-shadow:0 8px 30px rgba(108,99,255,.6)}

        /* ── SCROLL ANIMATIONS ── */
        .reveal,.reveal-l,.reveal-r{opacity:0;transition:opacity .7s ease,transform .7s ease}
        .reveal{transform:translateY(30px)}
        .reveal-l{transform:translateX(-40px)}
        .reveal-r{transform:translateX(40px)}
        .reveal.visible,.reveal-l.visible,.reveal-r.visible{opacity:1;transform:none}

        /* ── RESPONSIVE ── */
        @media(max-width:991px){section{padding:70px 0}.hero-photo,.hero-avatar{width:220px;height:220px}}
        @media(max-width:767px){.hero-photo,.hero-avatar{width:180px;height:180px;font-size:5rem}#mainNav{padding:10px 0}}
        @media(max-width:575px){.hero-name{font-size:2.2rem}}
    </style>
</head>
<body>

<!-- LOADER -->
<div id="loader" aria-hidden="true"><div class="loader-ring"></div></div>

<!-- BG -->
<div class="bg-wrap" aria-hidden="true">
    <div class="blob blob-1"></div>
    <div class="blob blob-2"></div>
    <div class="blob blob-3"></div>
</div>

<!-- ══════════════ NAVBAR ══════════════ -->
<nav id="mainNav" class="navbar navbar-expand-lg" role="navigation" aria-label="Main navigation">
    <div class="container">
        <a class="nav-brand navbar-brand" href="#hero" id="nav-brand-name">{{ personal.name }}</a>
        <button class="navbar-toggler border-0 p-0 ms-auto me-3" type="button"
                data-bs-toggle="collapse" data-bs-target="#navContent"
                aria-controls="navContent" aria-expanded="false" aria-label="Toggle navigation">
            <i class="bi bi-list" style="color:var(--text-primary);font-size:1.5rem;"></i>
        </button>
        <div class="collapse navbar-collapse" id="navContent">
            <ul class="navbar-nav mx-auto gap-1">
                <li class="nav-item"><a class="nav-link nav-link-custom" href="#about">About</a></li>
                <li class="nav-item"><a class="nav-link nav-link-custom" href="#skills">Skills</a></li>
                <li class="nav-item"><a class="nav-link nav-link-custom" href="#experience">Experience</a></li>
                <li class="nav-item"><a class="nav-link nav-link-custom" href="#education">Education</a></li>
                <li class="nav-item"><a class="nav-link nav-link-custom" href="#projects">Projects</a></li>
                <li class="nav-item"><a class="nav-link nav-link-custom" href="#services">Services</a></li>
                <li class="nav-item"><a class="nav-link nav-link-custom" href="#certificates">Certs</a></li>
                <li class="nav-item"><a class="nav-link nav-link-custom" href="#contact">Contact</a></li>
            </ul>
            <div class="d-flex align-items-center gap-3 mt-3 mt-lg-0">
                <button class="theme-btn" id="themeToggle" aria-label="Toggle dark/light mode">
                    <i class="bi bi-sun-fill" id="themeIcon"></i>
                </button>
                <a href="{{ personal.resume_url }}" class="btn-grd" target="_blank" rel="noopener" id="nav-resume-btn" aria-label="Download Resume">
                    <i class="bi bi-download" aria-hidden="true"></i> Resume
                </a>
            </div>
        </div>
    </div>
</nav>

<!-- ══════════════ HERO ══════════════ -->
<section id="hero" aria-label="Introduction">
    <div class="container">
        <div class="row align-items-center g-5">
            <div class="col-lg-7 order-2 order-lg-1">
                <div class="hero-badge"><span class="dot"></span>Available for opportunities</div>
                <h1 class="hero-name" id="hero-name">{{ personal.name }}</h1>
                <p class="hero-title" id="hero-title"><i class="bi bi-code-slash me-2" aria-hidden="true"></i>{{ personal.title }}</p>
                <p class="hero-tagline" id="hero-tagline">{{ personal.tagline }}</p>
                <div class="d-flex flex-wrap gap-3 mb-4">
                    <a href="#projects" class="btn-grd"><i class="bi bi-grid-3x3-gap-fill" aria-hidden="true"></i>View Projects</a>
                    <a href="#contact" class="btn-outline-gl"><i class="bi bi-envelope" aria-hidden="true"></i>Contact Me</a>
                </div>
                <!-- Social Links -->
                <div class="social-links d-flex gap-2 mb-5" aria-label="Social media">
                    <a href="{{ social.github }}" target="_blank" rel="noopener" id="social-github" aria-label="GitHub"><i class="bi bi-github"></i></a>
                    <a href="{{ social.linkedin }}" target="_blank" rel="noopener" id="social-linkedin" aria-label="LinkedIn"><i class="bi bi-linkedin"></i></a>
                    <a href="{{ social.twitter }}" target="_blank" rel="noopener" id="social-twitter" aria-label="Twitter"><i class="bi bi-twitter-x"></i></a>
                    <a href="{{ social.instagram }}" target="_blank" rel="noopener" id="social-instagram" aria-label="Instagram"><i class="bi bi-instagram"></i></a>
                    <a href="mailto:{{ personal.email }}" id="social-email" aria-label="Email"><i class="bi bi-envelope-fill"></i></a>
                </div>
                <!-- Stats -->
                <div class="row g-3">
                    <div class="col-4"><div class="glass-card stat-card"><div class="stat-num">3+</div><div class="stat-label">Years Exp.</div></div></div>
                    <div class="col-4"><div class="glass-card stat-card"><div class="stat-num">20+</div><div class="stat-label">Projects</div></div></div>
                    <div class="col-4"><div class="glass-card stat-card"><div class="stat-num">100%</div><div class="stat-label">Committed</div></div></div>
                </div>
            </div>
            <div class="col-lg-5 order-1 order-lg-2 text-center">
                <div class="hero-photo-wrap d-inline-block">
                    <img src="{{ personal.photo }}" alt="{{ personal.name }} profile photo" class="hero-photo" id="hero-photo" loading="eager" onerror="this.style.display='none';document.getElementById('hero-avatar').style.display='flex'">
                    <div class="hero-avatar" id="hero-avatar" style="display:none;" aria-label="{{ personal.name }}">
                        <span id="hero-initial">?</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- ══════════════ ABOUT ══════════════ -->
<section id="about" aria-label="About me">
    <div class="container">
        <div class="row align-items-center g-5">
            <div class="col-lg-5 reveal-l">
                <div class="text-center position-relative">
                    <img src="{{ personal.photo }}" alt="{{ personal.name }}" class="about-photo glass-card" id="about-photo" loading="lazy" onerror="this.style.display='none';document.getElementById('about-fallback').style.display='flex'">
                    <div class="about-fallback glass-card" id="about-fallback" style="display:none;"><i class="bi bi-person" aria-hidden="true"></i></div>
                </div>
            </div>
            <div class="col-lg-7 reveal-r">
                <div class="section-badge">About Me</div>
                <h2 class="section-title">Who Am I?</h2>
                <p class="section-sub mb-4" id="about-text">{{ personal.about }}</p>
                <div class="mb-4">
                    <div class="info-row"><i class="bi bi-envelope-fill" aria-hidden="true"></i><div><div class="info-lbl">Email</div><div class="info-val" id="about-email">{{ personal.email }}</div></div></div>
                    <div class="info-row"><i class="bi bi-telephone-fill" aria-hidden="true"></i><div><div class="info-lbl">Phone</div><div class="info-val" id="about-phone">{{ personal.phone }}</div></div></div>
                    <div class="info-row"><i class="bi bi-geo-alt-fill" aria-hidden="true"></i><div><div class="info-lbl">Location</div><div class="info-val" id="about-address">{{ personal.address }}</div></div></div>
                </div>
                <div class="d-flex gap-3">
                    <a href="{{ personal.resume_url }}" class="btn-grd" target="_blank" rel="noopener" id="about-resume-btn"><i class="bi bi-download" aria-hidden="true"></i>Download CV</a>
                    <a href="#contact" class="btn-outline-gl"><i class="bi bi-chat-dots" aria-hidden="true"></i>Let's Talk</a>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- ══════════════ SKILLS ══════════════ -->
<section id="skills" aria-label="Skills and technologies">
    <div class="container">
        <div class="text-center mb-5 reveal">
            <div class="section-badge">Expertise</div>
            <h2 class="section-title">Skills & Technologies</h2>
            <p class="section-sub mx-auto">Technologies and tools I use to build exceptional digital experiences.</p>
        </div>
        <div class="row g-4" id="skills-grid">
            <div class="col-lg-6 reveal">
                <div class="glass-card p-4 h-100">
                    <div class="skill-cat"><i class="bi bi-code-slash me-2"></i>Technical Skills</div>
                    <div class="d-flex flex-wrap gap-2" id="sk-technical">
                        <span class="skill-tag sk-tech">Loading...</span>
                    </div>
                </div>
            </div>
            <div class="col-lg-6 reveal">
                <div class="glass-card p-4 h-100">
                    <div class="skill-cat"><i class="bi bi-boxes me-2"></i>Frameworks &amp; Libraries</div>
                    <div class="d-flex flex-wrap gap-2" id="sk-frameworks">
                        <span class="skill-tag sk-fw">Loading...</span>
                    </div>
                </div>
            </div>
            <div class="col-lg-6 reveal">
                <div class="glass-card p-4 h-100">
                    <div class="skill-cat"><i class="bi bi-tools me-2"></i>Tools &amp; DevOps</div>
                    <div class="d-flex flex-wrap gap-2" id="sk-tools">
                        <span class="skill-tag sk-tool">Loading...</span>
                    </div>
                </div>
            </div>
            <div class="col-lg-6 reveal">
                <div class="glass-card p-4 h-100">
                    <div class="skill-cat"><i class="bi bi-people me-2"></i>Soft Skills</div>
                    <div class="d-flex flex-wrap gap-2" id="sk-soft">
                        <span class="skill-tag sk-soft">Loading...</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <!-- Data store for JS population -->
    <div style="display:none">
        <span id="data-sk-technical">{{ skills.technical }}</span>
        <span id="data-sk-frameworks">{{ skills.frameworks }}</span>
        <span id="data-sk-tools">{{ skills.tools }}</span>
        <span id="data-sk-soft">{{ skills.soft }}</span>
        <span id="data-sk-languages">{{ skills.languages }}</span>
    </div>
</section>

<!-- ══════════════ EXPERIENCE ══════════════ -->
<section id="experience" aria-label="Work experience">
    <div class="container">
        <div class="text-center mb-5 reveal">
            <div class="section-badge">Career</div>
            <h2 class="section-title">Work Experience</h2>
        </div>
        <div class="row">
            <div class="col-lg-8 mx-auto">
                <div class="timeline" role="list" id="exp-timeline">
                    <!-- Populated by mapping / JS -->
                    <div class="tl-item reveal" role="listitem">
                        <div class="tl-dot" aria-hidden="true"></div>
                        <div class="tl-card">
                            <span class="tl-period"><i class="bi bi-calendar2" aria-hidden="true"></i><span id="exp-duration">{{ experience.duration }}</span></span>
                            <div class="tl-role" id="exp-position">{{ experience.position }}</div>
                            <div class="tl-org" id="exp-company">{{ experience.company }}</div>
                            <p class="tl-desc" id="exp-description">{{ experience.description }}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- ══════════════ EDUCATION ══════════════ -->
<section id="education" aria-label="Education">
    <div class="container">
        <div class="text-center mb-5 reveal">
            <div class="section-badge">Learning</div>
            <h2 class="section-title">Education</h2>
        </div>
        <div class="row">
            <div class="col-lg-8 mx-auto">
                <div class="timeline" role="list" id="edu-timeline">
                    <div class="tl-item reveal" role="listitem">
                        <div class="tl-dot" aria-hidden="true"></div>
                        <div class="tl-card">
                            <span class="tl-period"><i class="bi bi-calendar2" aria-hidden="true"></i><span id="edu-year">{{ education.year }}</span></span>
                            <div class="tl-role" id="edu-degree">{{ education.degree }}</div>
                            <div class="tl-org" id="edu-university">{{ education.university }}</div>
                            <p class="tl-desc" id="edu-college">{{ education.college }}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- ══════════════ PROJECTS ══════════════ -->
<section id="projects" aria-label="Portfolio projects">
    <div class="container">
        <div class="text-center mb-5 reveal">
            <div class="section-badge">Work</div>
            <h2 class="section-title">Featured Projects</h2>
            <p class="section-sub mx-auto">A curated collection of my best work.</p>
        </div>
        <div class="filter-bar reveal" role="tablist" aria-label="Filter projects">
            <button class="filter-btn active" data-filter="all" role="tab" aria-selected="true">All</button>
            <button class="filter-btn" data-filter="web" role="tab" aria-selected="false">Web</button>
            <button class="filter-btn" data-filter="mobile" role="tab" aria-selected="false">Mobile</button>
            <button class="filter-btn" data-filter="ai" role="tab" aria-selected="false">AI / ML</button>
            <button class="filter-btn" data-filter="design" role="tab" aria-selected="false">Design</button>
        </div>
        <div class="row g-4" id="projects-grid">
            <!-- Primary project card rendered from mapping -->
            <div class="col-md-6 col-lg-4 project-item reveal" data-category="web">
                <article class="proj-card">
                    <div class="proj-img-wrap">
                        <img src="{{ projects.image }}" alt="{{ projects.title }}" id="proj-img" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
                        <div class="proj-placeholder" style="display:none"><i class="bi bi-code-square" aria-hidden="true"></i></div>
                        <div class="proj-overlay">
                            <a href="{{ projects.github_url }}" target="_blank" rel="noopener" id="proj-github" aria-label="View on GitHub"><i class="bi bi-github" aria-hidden="true"></i> Code</a>
                            <a href="{{ projects.live_url }}" target="_blank" rel="noopener" id="proj-live" aria-label="View live demo"><i class="bi bi-box-arrow-up-right" aria-hidden="true"></i> Live</a>
                        </div>
                    </div>
                    <div class="proj-body">
                        <div class="proj-tags" id="proj-tags"></div>
                        <h3 class="proj-title" id="proj-title">{{ projects.title }}</h3>
                        <p class="proj-desc" id="proj-desc">{{ projects.description }}</p>
                    </div>
                </article>
            </div>
        </div>
    </div>
    <div style="display:none"><span id="data-proj-tech">{{ projects.tech }}</span></div>
</section>

<!-- ══════════════ SERVICES ══════════════ -->
<section id="services" aria-label="Services">
    <div class="container">
        <div class="text-center mb-5 reveal">
            <div class="section-badge">Offerings</div>
            <h2 class="section-title">Services</h2>
            <p class="section-sub mx-auto">What I can do for you.</p>
        </div>
        <div class="row g-4" id="services-grid">
            <div class="col-md-6 col-lg-4 reveal">
                <article class="glass-card svc-card h-100">
                    <div class="svc-icon" aria-hidden="true"><i class="bi bi-star-fill"></i></div>
                    <h3 class="svc-title" id="svc-title">{{ services.title }}</h3>
                    <p class="svc-desc" id="svc-desc">{{ services.description }}</p>
                </article>
            </div>
            <div class="col-md-6 col-lg-4 reveal">
                <article class="glass-card svc-card h-100">
                    <div class="svc-icon" aria-hidden="true"><i class="bi bi-laptop"></i></div>
                    <h3 class="svc-title">Web Development</h3>
                    <p class="svc-desc">Full-stack web applications with modern frameworks, responsive design, and optimized performance.</p>
                </article>
            </div>
            <div class="col-md-6 col-lg-4 reveal">
                <article class="glass-card svc-card h-100">
                    <div class="svc-icon" aria-hidden="true"><i class="bi bi-phone"></i></div>
                    <h3 class="svc-title">Mobile Development</h3>
                    <p class="svc-desc">Cross-platform mobile apps delivering native-like performance across iOS and Android.</p>
                </article>
            </div>
        </div>
    </div>
</section>

<!-- ══════════════ CERTIFICATES ══════════════ -->
<section id="certificates" aria-label="Certifications">
    <div class="container">
        <div class="text-center mb-5 reveal">
            <div class="section-badge">Credentials</div>
            <h2 class="section-title">Certifications</h2>
        </div>
        <div class="row g-4" id="certs-grid">
            <div class="col-md-6 col-lg-4 reveal">
                <div class="glass-card cert-card">
                    <div class="cert-icon" aria-hidden="true"><i class="bi bi-award-fill"></i></div>
                    <div>
                        <div class="cert-name" id="cert-name">{{ certificates.name }}</div>
                        <div class="cert-issuer" id="cert-issuer">{{ certificates.issuer }}</div>
                        <div class="cert-year" id="cert-year"><i class="bi bi-calendar2 me-1" aria-hidden="true"></i>{{ certificates.year }}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- ══════════════ ACHIEVEMENTS ══════════════ -->
<section id="achievements" aria-label="Achievements">
    <div class="container">
        <div class="text-center mb-5 reveal">
            <div class="section-badge">Recognition</div>
            <h2 class="section-title">Achievements</h2>
        </div>
        <div class="row g-4" id="ach-grid">
            <div class="col-md-6 col-lg-4 reveal">
                <div class="glass-card ach-card">
                    <div class="ach-icon" aria-hidden="true"><i class="bi bi-trophy-fill"></i></div>
                    <div>
                        <div class="ach-title" id="ach-title">{{ achievements.title }}</div>
                        <p class="ach-desc" id="ach-desc">{{ achievements.description }}</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- ══════════════ CONTACT ══════════════ -->
<section id="contact" aria-label="Contact">
    <div class="container">
        <div class="text-center mb-5 reveal">
            <div class="section-badge">Get In Touch</div>
            <h2 class="section-title">Let's Work Together</h2>
            <p class="section-sub mx-auto">Have a project in mind? Send me a message and let's create something amazing.</p>
        </div>
        <div class="row g-5">
            <div class="col-lg-4 reveal-l">
                <div class="glass-card contact-info">
                    <div class="contact-icon"><i class="bi bi-envelope-fill" aria-hidden="true"></i></div>
                    <div><div class="contact-lbl">Email</div><div class="contact-val" id="contact-email">{{ personal.email }}</div></div>
                </div>
                <div class="glass-card contact-info">
                    <div class="contact-icon"><i class="bi bi-telephone-fill" aria-hidden="true"></i></div>
                    <div><div class="contact-lbl">Phone</div><div class="contact-val" id="contact-phone">{{ personal.phone }}</div></div>
                </div>
                <div class="glass-card contact-info">
                    <div class="contact-icon"><i class="bi bi-geo-alt-fill" aria-hidden="true"></i></div>
                    <div><div class="contact-lbl">Location</div><div class="contact-val" id="contact-address">{{ personal.address }}</div></div>
                </div>
                <div class="social-links d-flex flex-wrap gap-2 mt-4">
                    <a href="{{ social.github }}" target="_blank" rel="noopener" aria-label="GitHub"><i class="bi bi-github"></i></a>
                    <a href="{{ social.linkedin }}" target="_blank" rel="noopener" aria-label="LinkedIn"><i class="bi bi-linkedin"></i></a>
                    <a href="{{ social.twitter }}" target="_blank" rel="noopener" aria-label="Twitter"><i class="bi bi-twitter-x"></i></a>
                </div>
            </div>
            <div class="col-lg-8 reveal-r">
                <div class="glass-card p-4 p-lg-5">
                    <h3 class="h5 mb-4" style="color:var(--text-primary);font-weight:700;">Send a Message</h3>
                    <form id="contact-form" novalidate aria-label="Contact form">
                        <div class="row g-3">
                            <div class="col-sm-6">
                                <label for="cName" class="form-label-gl">Full Name *</label>
                                <input type="text" id="cName" name="name" class="form-control form-gl" placeholder="Your name" required autocomplete="name" aria-required="true">
                            </div>
                            <div class="col-sm-6">
                                <label for="cEmail" class="form-label-gl">Email *</label>
                                <input type="email" id="cEmail" name="email" class="form-control form-gl" placeholder="your@email.com" required autocomplete="email" aria-required="true">
                            </div>
                            <div class="col-12">
                                <label for="cSubject" class="form-label-gl">Subject</label>
                                <input type="text" id="cSubject" name="subject" class="form-control form-gl" placeholder="What's this about?">
                            </div>
                            <div class="col-12">
                                <label for="cMessage" class="form-label-gl">Message *</label>
                                <textarea id="cMessage" name="message" class="form-control form-gl" rows="5" placeholder="Tell me about your project..." required aria-required="true"></textarea>
                            </div>
                            <div class="col-12">
                                <button type="submit" class="btn-grd w-100" style="justify-content:center;">
                                    <i class="bi bi-send-fill" aria-hidden="true"></i> Send Message
                                </button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- ══════════════ FOOTER ══════════════ -->
<footer role="contentinfo">
    <div class="container">
        <div class="row align-items-center">
            <div class="col-md-6 text-center text-md-start mb-3 mb-md-0">
                <div class="footer-brand mb-1" id="footer-name">{{ personal.name }}</div>
                <p class="footer-copy">&copy; <span id="footer-year"></span> {{ personal.name }}. All rights reserved.</p>
            </div>
            <div class="col-md-6 text-center text-md-end">
                <div class="social-links d-flex justify-content-center justify-content-md-end gap-2">
                    <a href="{{ social.github }}" target="_blank" rel="noopener" aria-label="GitHub"><i class="bi bi-github"></i></a>
                    <a href="{{ social.linkedin }}" target="_blank" rel="noopener" aria-label="LinkedIn"><i class="bi bi-linkedin"></i></a>
                    <a href="{{ social.twitter }}" target="_blank" rel="noopener" aria-label="Twitter"><i class="bi bi-twitter-x"></i></a>
                    <a href="{{ social.youtube }}" target="_blank" rel="noopener" aria-label="YouTube"><i class="bi bi-youtube"></i></a>
                </div>
            </div>
        </div>
    </div>
</footer>

<!-- BACK TO TOP -->
<button id="btt" aria-label="Back to top"><i class="bi bi-arrow-up" aria-hidden="true"></i></button>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
'use strict';

// ── LOADER ──
window.addEventListener('load', () => {
    const loader = document.getElementById('loader');
    if(loader){ loader.classList.add('hidden'); setTimeout(() => loader.remove(), 700); }
});

// ── FOOTER YEAR ──
const fyEl = document.getElementById('footer-year');
if(fyEl) fyEl.textContent = new Date().getFullYear();

// ── HERO INITIAL ──
const heroInitEl = document.getElementById('hero-initial');
const heroNameEl = document.getElementById('hero-name');
if(heroInitEl && heroNameEl){
    heroInitEl.textContent = (heroNameEl.textContent.trim()[0] || '?').toUpperCase();
}

// ── THEME TOGGLE ──
const html = document.documentElement;
const themeIcon = document.getElementById('themeIcon');
const themeToggle = document.getElementById('themeToggle');
const saved = localStorage.getItem('mg-theme') || 'dark';
html.setAttribute('data-theme', saved);
updateIcon(saved);
themeToggle && themeToggle.addEventListener('click', () => {
    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('mg-theme', next);
    updateIcon(next);
});
function updateIcon(t){ if(themeIcon) themeIcon.className = t === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill'; }

// ── STICKY NAV ──
const mainNav = document.getElementById('mainNav');
window.addEventListener('scroll', () => { mainNav && mainNav.classList.toggle('scrolled', scrollY > 50); }, {passive:true});

// ── SCROLLSPY ──
const allSections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('.nav-link-custom');
const spy = new IntersectionObserver(entries => {
    entries.forEach(e => {
        if(e.isIntersecting){
            navLinks.forEach(l => {
                l.classList.remove('active');
                if(l.getAttribute('href') === '#' + e.target.id){ l.classList.add('active'); }
            });
        }
    });
}, { threshold:0.35, rootMargin:'-60px 0px -60px 0px' });
allSections.forEach(s => spy.observe(s));

// ── REVEAL ANIMATIONS ──
const revealObs = new IntersectionObserver(entries => {
    entries.forEach(e => { if(e.isIntersecting){ e.target.classList.add('visible'); revealObs.unobserve(e.target); } });
}, { threshold:0.1, rootMargin:'0px 0px -40px 0px' });
document.querySelectorAll('.reveal,.reveal-l,.reveal-r,.tl-item').forEach(el => revealObs.observe(el));

// ── BACK TO TOP ──
const btt = document.getElementById('btt');
window.addEventListener('scroll', () => { btt && btt.classList.toggle('visible', scrollY > 400); }, {passive:true});
btt && btt.addEventListener('click', () => window.scrollTo({top:0, behavior:'smooth'}));

// ── PROJECT FILTERS ──
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => { b.classList.remove('active'); b.setAttribute('aria-selected','false'); });
        btn.classList.add('active'); btn.setAttribute('aria-selected','true');
        const f = btn.dataset.filter;
        document.querySelectorAll('.project-item').forEach(item => {
            item.style.display = (f==='all' || item.dataset.category===f) ? '' : 'none';
        });
    });
});

// ── POPULATE SKILLS FROM DATA SPANS ──
function populateSkills(containerId, dataId, cssClass) {
    const data = document.getElementById(dataId);
    const container = document.getElementById(containerId);
    if(!data || !container) return;
    const text = data.textContent.trim();
    if(!text || text.includes('{{')) return; // raw placeholder = not injected yet
    container.innerHTML = '';
    text.split(',').forEach(sk => {
        const s = sk.trim();
        if(s){ const span = document.createElement('span'); span.className = 'skill-tag ' + cssClass; span.textContent = s; container.appendChild(span); }
    });
}
populateSkills('sk-technical','data-sk-technical','sk-tech');
populateSkills('sk-frameworks','data-sk-frameworks','sk-fw');
populateSkills('sk-tools','data-sk-tools','sk-tool');
populateSkills('sk-soft','data-sk-soft','sk-soft');

// ── POPULATE PROJECT TAGS ──
const techData = document.getElementById('data-proj-tech');
const projTagsEl = document.getElementById('proj-tags');
if(techData && projTagsEl){
    const t = techData.textContent.trim();
    if(t && !t.includes('{{')){
        projTagsEl.innerHTML = '';
        t.split(',').forEach(tag => {
            const span = document.createElement('span'); span.className='proj-tag'; span.textContent=tag.trim(); projTagsEl.appendChild(span);
        });
    }
}

// ── GLASS CARD MOUSEMOVE GLOW ──
document.querySelectorAll('.glass-card').forEach(card => {
    card.addEventListener('mousemove', e => {
        const r = card.getBoundingClientRect();
        const x = ((e.clientX - r.left) / r.width) * 100;
        const y = ((e.clientY - r.top) / r.height) * 100;
        card.style.background = `radial-gradient(circle at ${x}% ${y}%, rgba(108,99,255,.09), var(--glass-bg))`;
    });
    card.addEventListener('mouseleave', () => { card.style.background = ''; });
});

// ── CONTACT FORM VALIDATION ──
document.getElementById('contact-form') && document.getElementById('contact-form').addEventListener('submit', e => {
    e.preventDefault();
    const name = document.getElementById('cName');
    const email = document.getElementById('cEmail');
    const msg = document.getElementById('cMessage');
    let ok = true;
    [name, email, msg].forEach(f => {
        if(!f) return;
        const valid = f.value.trim() && (f.type!=='email' || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.value));
        f.style.borderColor = valid ? '' : '#f87171';
        if(!valid) ok = false;
    });
    if(ok){
        const btn = e.target.querySelector('button[type="submit"]');
        if(btn){ btn.textContent = 'Message Sent!'; btn.style.background='linear-gradient(135deg,#10b981,#059669)'; }
    }
});
</script>
</body>
</html>"""


MANIFEST_JSON = json.dumps({
    "name": "Modern Glass",
    "slug": "modern-glass",
    "version": "1.0.0",
    "author": "AI Portfolio Team",
    "description": "A premium glassmorphism portfolio theme with dark/light mode, Bootstrap 5, smooth animations, and full section coverage.",
    "category": "Premium",
    "layout": "single-page",
    "supports_dark_mode": True,
    "supports_blog": False,
    "supports_gallery": True,
    "supports_resume": True,
    "supports_contact_form": True,
    "color_accent": "#6c63ff",
    "font_family": "Inter, Space Grotesk",
    "tags": "glassmorphism, dark, premium, bootstrap, animated, modern"
}, indent=2)


# ── CSS SELECTOR → FIELD MAPPINGS ─────────────────────────────────────────────
# Each entry: (field_key, css_selector, attribute_type)
MAPPING_FIELDS = [
    # Personal
    ("personal.name",       "#hero-name",           "text"),
    ("personal.name",       "#nav-brand-name",      "text"),
    ("personal.name",       "#footer-name",         "text"),
    ("personal.title",      "#hero-title",          "text"),
    ("personal.tagline",    "#hero-tagline",        "text"),
    ("personal.about",      "#about-text",          "text"),
    ("personal.photo",      "#hero-photo",          "src"),
    ("personal.photo",      "#about-photo",         "src"),
    ("personal.email",      "#about-email",         "text"),
    ("personal.email",      "#contact-email",       "text"),
    ("personal.phone",      "#about-phone",         "text"),
    ("personal.phone",      "#contact-phone",       "text"),
    ("personal.address",    "#about-address",       "text"),
    ("personal.address",    "#contact-address",     "text"),
    ("personal.resume_url", "#nav-resume-btn",      "href"),
    ("personal.resume_url", "#about-resume-btn",    "href"),
    # Social
    ("social.github",       "#social-github",       "href"),
    ("social.linkedin",     "#social-linkedin",     "href"),
    ("social.twitter",      "#social-twitter",      "href"),
    ("social.instagram",    "#social-instagram",    "href"),
    ("social.email",        "#social-email",        "href"),
    # Experience
    ("experience.duration",    "#exp-duration",     "text"),
    ("experience.position",    "#exp-position",     "text"),
    ("experience.company",     "#exp-company",      "text"),
    ("experience.description", "#exp-description",  "text"),
    # Education
    ("education.year",      "#edu-year",            "text"),
    ("education.degree",    "#edu-degree",          "text"),
    ("education.university","#edu-university",      "text"),
    ("education.college",   "#edu-college",         "text"),
    # Projects
    ("projects.title",      "#proj-title",          "text"),
    ("projects.description","#proj-desc",           "text"),
    ("projects.image",      "#proj-img",            "src"),
    ("projects.github_url", "#proj-github",         "href"),
    ("projects.live_url",   "#proj-live",           "href"),
    # Services
    ("services.title",      "#svc-title",           "text"),
    ("services.description","#svc-desc",            "text"),
    # Certificates
    ("certificates.name",   "#cert-name",           "text"),
    ("certificates.issuer", "#cert-issuer",         "text"),
    ("certificates.year",   "#cert-year",           "text"),
    # Achievements
    ("achievements.title",       "#ach-title",      "text"),
    ("achievements.description", "#ach-desc",       "text"),
]


class Command(BaseCommand):
    help = "Install the Modern Glass theme into the database and mark it APPROVED."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-install theme even if it already exists (removes old files first).",
        )

    def handle(self, *args, **options):
        from themes.models import Theme, ThemeCategory
        from themes.services import process_theme_upload

        force = options["force"]
        slug = "modern-glass"

        # ── Check existing ──
        existing = Theme.objects.filter(slug=slug).first()
        if existing and not force:
            self.stdout.write(self.style.WARNING(
                f"Theme '{slug}' already exists (pk={existing.pk}). Use --force to reinstall."
            ))
            return

        if existing and force:
            self.stdout.write(f"Removing existing theme '{slug}' (pk={existing.pk})...")
            dest = os.path.join(settings.MEDIA_ROOT, "themes", "extracted", slug)
            if os.path.exists(dest):
                shutil.rmtree(dest, ignore_errors=True)
            existing.delete()
            self.stdout.write(self.style.WARNING("Old theme deleted."))

        # ── Category ──
        category, _ = ThemeCategory.objects.get_or_create(
            slug="premium",
            defaults={"name": "Premium", "icon": "bi-gem", "description": "Premium quality themes"}
        )

        # ── Get superuser for uploaded_by ──
        admin_user = User.objects.filter(is_superuser=True).first()

        # ── Create Theme DB record ──
        theme = Theme.objects.create(
            name="Modern Glass",
            slug=slug,
            description="A premium glassmorphism portfolio theme with dark/light mode, Bootstrap 5, smooth animations, and full section coverage.",
            author="AI Portfolio Team",
            category=category,
            uploaded_by=admin_user,
            status=Theme.Status.DRAFT,
            is_premium=False,
            price=0.00,
            font_family="Inter, Space Grotesk",
            supports_dark_mode=True,
            supports_custom_colors=True,
            supports_custom_fonts=True,
            supports_animation=True,
            is_active=True,
            display_order=1,
            version="1.0.0",
            tags="glassmorphism, dark, premium, bootstrap, animated, modern",
        )
        self.stdout.write(f"Created Theme record pk={theme.pk}")

        # ── Build ZIP in-memory ──
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", INDEX_HTML)
            zf.writestr("manifest.json", MANIFEST_JSON)
        zip_buffer.seek(0)
        self.stdout.write("ZIP package built in memory.")

        # ── Process upload (extract + scan + thumbnail) ──
        try:
            process_theme_upload(theme, zip_buffer)
            self.stdout.write(self.style.SUCCESS("Theme extracted and assets scanned."))
        except Exception as exc:
            theme.delete()
            raise CommandError(f"process_theme_upload failed: {exc}") from exc

        # ── Approve the theme ──
        theme.status = Theme.Status.APPROVED
        theme.save(update_fields=["status"])
        self.stdout.write(self.style.SUCCESS("Theme status set to APPROVED."))

        self.stdout.write(self.style.SUCCESS(
            f"\n[DONE] Modern Glass theme installed successfully!\n"
            f"  Theme PK      : {theme.pk}\n"
            f"  Slug          : {theme.slug}\n"
            f"  Status        : {theme.status}\n"
            f"  Extracted to  : {theme.extracted_path}\n"
            f"  Admin URL     : /admin/themes/theme/{theme.pk}/change/\n"
        ))
