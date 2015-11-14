import torch
from torch import nn, optim
from torch.autograd import Variable
from torch.utils.data import DataLoader
import argparse
import os

from scipy.io import wavfile
from dataset import *
from lstm import get_model
from audio_op import *
from config import *

def writeWav(fn, fs, data):
    data = data * 1.5 / np.max(np.abs(data))
    wavfile.write(fn, fs, data)

def bss_eval_global(mixed_wav, src1_wav, src2_wav, pred_src1_wav, pred_src2_wav):
    len_cropped = pred_src1_wav.shape[-1]
    src1_wav = src1_wav[:len_cropped]
    src2_wav = src2_wav[:len_cropped]
    mixed_wav = mixed_wav[:len_cropped]
    gnsdr, gsir, gsar = np.zeros(2), np.zeros(2), np.zeros(2)
    total_len = 0

    sdr, sir, sar, _ = bss_eval_sources(np.array([src1_wav, src2_wav]),
                                        np.array([pred_src1_wav, pred_src2_wav]), False)
    sdr_mixed, _, _, _ = bss_eval_sources(np.array([src1_wav, src2_wav]),
                                          np.array([mixed_wav, mixed_wav]), False)
    nsdr = sdr - sdr_mixed
    gnsdr += len_cropped * nsdr
    gsir += len_cropped * sir
    gsar += len_cropped * sar
    total_len += len_cropped
    gnsdr = gnsdr / total_len
    gsir = gsir / total_len
    gsar = gsar / total_len
    return gnsdr, gsir, gsar


# TF example
#    def add_loss_op(self, target):
#         self.target = target  # for outputting later
#         real_target = abs(target)
#         delta = self.output - real_target 
#         squared_error = tf.reduce_mean(tf.pow(delta, 2)) 

#         l2_cost = tf.reduce_mean([tf.norm(v) for v in tf.trainable_variables() if len(v.get_shape().as_list()) == 3])
#         self.loss = Config.l2_lambda * l2_cost + squared_error
#         tf.summary.scalar("loss", self.loss)
#         masked_loss = tf.abs(self.soft_masked_output) - real_target
#         self.masked_loss = Config.l2_lambda * l2_cost + tf.reduce_mean(tf.pow(masked_loss, 2))
#         tf.summary.scalar('masked_loss', self.masked_loss)
#         tf.summary.scalar('regularization_cost', Config.l2_lambda * l2_cost)
 
    
    
def main(args):
    num_epoches = args.num_epoches
    learning_rate = args.learning_rate
    batch_size = args.batch_size
    result_wav_dir = './results'
    
    train_dataset = iKala(args.len_frame, args.len_hop)
    train_loader = DataLoader(dataset = train_dataset, batch_size = batch_size)
    
    model = get_model(args)
    use_gpu = torch.cuda.is_available()  # 
    if use_gpu:
        model = model.cuda()
        
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    for epoch in range(num_epoches):
        print('epoch {}'.format(epoch + 1))
        running_loss = 0.0
        running_acc = 0.0
        for i, (inputs, target) in enumerate(train_loader):
            
            model.train()

            # Variable
            if use_gpu:
                inputs= Variable(inputs).cuda()
                target = Variable(target).cuda()
            else:
                inputs= Variable(inputs)
                target = Variable(target)

            out = model(inputs)
            
            
            # Soft Masking        
#             soft_song_mask = tf.abs(song_out) / (tf.abs(song_out) + tf.abs(voice_out) + 1e-10)s
#             soft_voice_mask = 1 - soft_song_mask
#             input_spec_curr = self.input[:,:,1]  # current frame of input spec
#             soft_song_output = apply_mask(input_spec_curr, soft_song_mask)
#             soft_voice_output = apply_mask(input_spec_curr, soft_voice_mask)
#             self.soft_masked_output = tf.concat([soft_song_output, soft_voice_output], axis=1)
            
            
            
            # loss
            loss = criterion(out, target)
            running_loss += loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            print('[{}/{}] Loss: {:.6f}'.format(
                epoch + 1, num_epoches, running_loss / (batch_size * i + 1e-4),
                running_acc / (batch_size * i +  1e-4)))

            
            song_spec_out, voice_spec_out = np.split(out.data.cpu().numpy(), 2, 2)
            
            song_spec_out = reals_to_complex_batch(song_spec_out)
            voice_spec_out = reals_to_complex_batch(voice_spec_out)
            
            
            for batch_item in range(batch_size):
                song_audio = create_audio_from_spectrogram(song_spec_out[batch_item,:,:], args)
                voice_audio = create_audio_from_spectrogram(voice_spec_out[batch_item,:,:], args)
                
                writeWav(os.path.join(result_wav_dir, 'song_%d_%d.wav' % (i, batch_item)), 
                         args.sample_rate, song_audio)
                writeWav(os.path.join(result_wav_dir, 'voice_%d_%d.wav' % (i, batch_item)), 
                         args.sample_rate, song_audio)
                print('=> done write :', '%d_%d' % (i, batch_item))

            
            # soft masking
        
            # eval   
        
if __name__ == '__main__':
    args = get_args()
    main(args)
    