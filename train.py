import keras as kr
import numpy as np
import tensorflow as tf
import pandas as pd
import optparse

import os
import matplotlib.pyplot as plt
from models import *

def prepInput(reshape=True,nrows=None):
  #data = pd.read_csv("CALQ_output_10x.csv")  ## big  300k file
  data = pd.read_csv("CALQ_output_10x.csv",nrows=nrows)  ## big  300k file
  
  normData = data.apply(lambda x: x/max(x),axis=1)
  inputdata = normData.values

  if reshape: 
    shaped_data = np.reshape(inputdata,(len(inputdata),12,4,1))
  else:
    shaped_data = inputdata
  
  validation_frac = 0.2
  N = round(len(shaped_data)*validation_frac)
  
  #randomly select 25% entries
  index = np.random.choice(shaped_data.shape[0], N, replace=False)  
  #select the indices of the other 75%
  full_index = np.array(range(0,len(shaped_data)))
  train_index = np.logical_not(np.in1d(full_index,index))
  
  val_input = shaped_data[index]
  train_input = shaped_data[train_index]

  #print(train_input.shape)
  #print(val_input.shape)

  return shaped_data,val_input,train_input

def train(autoencoder,train_input,val_input,name):

  es = kr.callbacks.callbacks.EarlyStopping(monitor='val_loss', mode='min', verbose=1, patience=5)
  history = autoencoder.fit(train_input,train_input,
                epochs=150,
                batch_size=200,
                shuffle=True,
                validation_data=(val_input,val_input),
                callbacks=[es]
                )

  plt.plot(history.history['loss'])
  plt.plot(history.history['val_loss'])
  plt.title('Model loss %s'%name)
  plt.ylabel('Loss')
  plt.xlabel('Epoch')
  plt.legend(['Train', 'Test'], loc='upper right')
  plt.savefig("history_%s.jpg"%name)
  #plt.show()

  
  json_string = autoencoder.to_json()
  with open('./%s.json'%name,'w') as f:
      f.write(json_string)
  autoencoder.save_weights('%s.hdf5'%name)

  return history

def predict(x,autoencoder,encoder,reshape=True):
  decoded_Q = autoencoder.predict(x)
  encoded_Q = encoder.predict(x)
 
  #need reshape for CNN layers  
  if reshape :
    decoded_Q = np.reshape(decoded_Q,(len(decoded_Q),12,4))
    encoded_shape = encoded_Q.shape
    encoded_Q = np.reshape(encoded_Q,(len(encoded_Q),encoded_shape[3],encoded_shape[1]))
  return decoded_Q, encoded_Q

### sum of squared difference
def SSD(x,y):
    ssd  = np.sum(((x-y)**2),(1,2)) ## sum x-y dim.
    return ssd

### cross correlation of input/output 
def cross_corr(x,y):
    cov = np.cov(x.flatten(),y.flatten())
    std = np.sqrt(np.diag(cov))
    corr = cov / np.multiply.outer(std, std)
    return corr[0,1]

def visualize(input_Q,decoded_Q,encoded_Q,Nevents=8,name='model_X'):
  #randomly pick Nevents
  index = np.random.choice(input_Q.shape[0], Nevents, replace=False)  
  
  inputImg    = input_Q[index]
  encodedImg  = encoded_Q[index]
  outputImg   = decoded_Q[index]
  
  fig, axs = plt.subplots(3, Nevents, figsize=(16, 10))
  
  for i in range(0,Nevents):
      if i==0:
          axs[0,i].set(xlabel='',ylabel='cell_y',title='Input_%i'%i)
      else:
          axs[0,i].set(xlabel='',title='Input_%i'%i)        
      c1=axs[0,i].imshow(inputImg[i])
 
  for i in range(0,Nevents):
      if i==0:
          axs[1,i].set(xlabel='cell_x',ylabel='cell_y',title='CNN Ouput_%i'%i)        
      else:
          axs[1,i].set(xlabel='cell_x',title='CNN Ouput_%i'%i)
      c1=axs[1,i].imshow(outputImg[i])
     
  for i in range(0,Nevents):
    if i==0:
        axs[2,i].set(xlabel='latent dim',ylabel='depth',title='Encoded_%i'%i)
    else:
        axs[2,i].set(xlabel='latent dim',title='Encoded_%i'%i)
    c1=axs[2,i].imshow(encodedImg[i])
    plt.colorbar(c1,ax=axs[2,i])
  
  plt.tight_layout()
  plt.savefig("%s_examples.jpg"%name)
  
  plt.show()

def vis1d(input_Q,decoded_Q,encoded_Q,index,name='model_X'):
  #Nevents = 50
  #index = np.random.choice(encoded_Q.shape[0], Nevents, replace=False)  
  
  fig, axs = plt.subplots(1, 4, figsize=(16, 5))
  fig.suptitle(name,fontsize=16)
  
  axs[0].set(xlabel='ChargeQ',title='Input layer')
  axs[1].set(xlabel='Encoded unit',title='Encoded layer')
  axs[2].set(xlabel='ChargeQ'     ,title='Decoded layer')
  axs[3].set(xlabel='(Decoded - Input)**2',title='(Decoded - Input)**2')
  c1=axs[0].imshow(input_Q[index])
  c2=axs[1].imshow(encoded_Q[index])
  c3=axs[2].imshow(decoded_Q[index])
  c4=axs[3].imshow((decoded_Q[index]-input_Q[index])**2)
  plt.colorbar(c1,ax=axs[0])
  plt.colorbar(c2,ax=axs[1])
  plt.colorbar(c3,ax=axs[2])
  plt.colorbar(c4,ax=axs[3])
  plt.savefig("%s.jpg"%name)
  #plt.show()

  def plothist(y,xlabel,name):
    plt.figure(figsize=(6,4))
    plt.hist(y,50)
    
    mu = np.mean(y)
    std = np.std(y)
    ax = plt.axes()
    plt.text(0.1, 0.9, name,transform=ax.transAxes)
    plt.text(0.1, 0.8, r'$\mu=%.3f,\ \sigma=%.3f$'%(mu,std),transform=ax.transAxes)
    plt.xlabel(xlabel)
    plt.ylabel('Entry')
    plt.title('%s on validation set'%xlabel)
    plt.savefig("hist_%s.jpg"%name)
    #plt.show()

  cross_corr_arr = np.array( [cross_corr(input_Q[i],decoded_Q[i]) for i in range(0,len(decoded_Q))]  )
  ssd_arr        = np.sum((input_Q-decoded_Q)**2,1)

  plothist(cross_corr_arr,'cross correlation',name+"_corr")
  plothist(ssd_arr,'sum squared difference',name+"_ssd")

  return cross_corr_arr,ssd_arr

def trainDeepAutoEncoder(options,args):

  nrows = 30000
  Nevents = 50
  full_input, val_input, train_input = prepInput(reshape=False,nrows=nrows)

  index = np.random.choice(val_input.shape[0], Nevents, replace=False)  
  models = [
    {'dims':[48,24,12,6  ]         ,'ws':'./deepAutos_48_24_12_6.hdf5'},
    {'dims':[48,24,12,6,4]         ,'ws':'./deepAutos_48_24_12_6_4.hdf5'},
    {'dims':[48,24,12,8,4]         ,'ws':'./deepAutos_48_24_12_8_4.hdf5'},
    {'dims':[48,24,12,6,3]         ,'ws':'./deepAutos_48_24_12_6_3.hdf5'},
    {'dims':[48,24,12,6,2]         ,'ws':'./deepAutos_48_24_12_6_2.hdf5'},
    {'dims':[48,24,12,10,6  ]      ,'ws':'./deepAutos_48_24_12_10_6.hdf5'},
    {'dims':[48,24,12,10,10,10,6  ],'ws':'./deepAutos_48_24_12_10_10_10_6.hdf5'},
    {'dims':[48,6,2]               ,'ws':'./deepAutos_48_6_2.hdf5'}     
  ]

  summary = pd.DataFrame(columns=['name','corr','ssd'])
  os.chdir('./deepAutos/')
  for model in models:
    dims = model['dims']
    model_name = "deepAutos_"+"_".join([str(d) for d in dims])
    if not os.path.exists(model_name):
      os.mkdir(model_name)
    os.chdir(model_name)
    m_deepAuto, m_deepAutoEn = deepAuto(dims,model['ws'])
    #m_deepAuto.summary()
    #m_deepAutoEn.summary()
    if model['ws']=='':
      history = train(m_deepAuto,train_input,val_input,name=model_name)
    deQ, enQ = predict(val_input,m_deepAuto,m_deepAutoEn,False)
    corr_arr, ssd_arr = vis1d(val_input,deQ,enQ,index,model_name)
    model['corr'] = np.round(np.mean(corr_arr),3)
    model['ssd'] = np.round(np.mean(ssd_arr),3)

    summary = summary.append({'name':model_name,'corr':model['corr'],'ssd':model['ssd']},ignore_index=True)
    for k in model.keys():
      print(k,model[k])
    os.chdir('../')
  print(summary)

def main(options,args):
  full_input, val_input, train_input = prepInput(reshape=False)

  w_CNN  = 'autoencoder_CNN_16_8_4_full.hdf5'
  w_qCNN = 'autoencoder_qCNN_4bit_16_8_4.hdf5'
  m_autoCNN , m_autoCNNen                = autoCNN(weights_f=w_CNN)
  m_QautoCNN, m_QautoCNNen               = QautoCNN(weights_f=w_qCNN)

  #input_Q            = np.reshape(val_input,(len(val_input),12,4))
  #cnn_deQ ,cnn_enQ   = predict(val_input,m_autoCNN,m_autoCNNen)
  #qcnn_deQ,qcnn_enQ  = predict(val_input,m_QautoCNN,m_QautoCNNen)

  #history = train(m_autoCNN,train_input,val_input)  
  #visualize(input_Q,cnn_deQ,cnn_enQ,name='CNN_test')
  #print('CNN ssd: ' ,np.round(SSD(input_Q,cnn_deQ),3))



if __name__== "__main__":

    parser = optparse.OptionParser()
    parser.add_option('-o',"--odir", type="string", default = 'ntuple.root',dest="inputFile", help="input TSG ntuple")

    (options, args) = parser.parse_args()
    trainDeepAutoEncoder(options,args)
    #main(options,args)

