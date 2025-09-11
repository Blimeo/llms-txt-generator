import type { NextApiRequest, NextApiResponse } from 'next';


export default async function handler(req: NextApiRequest, res: NextApiResponse) {
    if (req.method === 'POST') {
        const { url, config } = req.body;
        // TODO: enqueue job in Redis (BullMQ)
        return res.status(200).json({ projectId: 'p_123', status: 'queued' });
    }
    res.setHeader('Allow', ['POST']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
}