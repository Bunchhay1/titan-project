import http from 'k6/http';
import { check, sleep } from 'k6';

// 🔥 កំណត់កម្លាំងទ័ព (Configuration)
export const options = {
  scenarios: {
    create_users: {
      executor: 'shared-iterations',
      vus: 40,               // 40 ក្រុមហ៊ុន (Running in parallel)
      iterations: 10000,     // ចំនួនសរុបដែលចង់បង្កើត (10k Users)
      maxDuration: '10m',    // រត់យ៉ាងយូរបំផុត ១០ នាទី
    },
  },
};

export default function () {
  // 🎲 បង្កើតទិន្នន័យ Random ដើម្បីកុំឱ្យជាន់គ្នា (Unique Data)
  const randomId = Math.floor(Math.random() * 1000000000);
  const username = `user_${randomId}`;
  const email = `user_${randomId}@titanbank.com`;

  // 📦 Payload (ត្រូវនឹងអ្វីដែលយើងតេស្តមុននេះ)
  const payload = JSON.stringify({
    firstname: "Auto",
    lastname: "Bot",
    username: username,
    email: email,
    password: "TitanStrongPass123!",
    rawPassword: "TitanStrongPass123!", // សំខាន់ណាស់!
    pin: "123456"
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  // 🚀 បាញ់ចូលតាម Localhost (លឿនជាង និងមិនជាប់ Cloudflare Limit)
  const res = http.post('http://localhost:8081/api/auth/register', payload, params);

  // ✅ ពិនិត្យលទ្ធផល
  check(res, {
    'is status 200 or 201': (r) => r.status === 200 || r.status === 201,
    'no error': (r) => r.status !== 500 && r.status !== 400,
  });
}