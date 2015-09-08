# Author: Kyle Kastner
# License: BSD 3-clause
import numpy as np
import theano
from theano import tensor


class sgd(object):
    """
    Vanilla SGD
    """
    def __init__(self, params):
        pass

    def updates(self, params, grads, learning_rate):
        updates = []
        for n, (param, grad) in enumerate(zip(params, grads)):
            updates.append((param, param - learning_rate * grad))
        return updates


class sgd_momentum(object):
    """
    SGD with momentum
    """
    def __init__(self, params):
        self.memory_ = [theano.shared(np.zeros_like(p.get_value()))
                        for p in params]

    def updates(self, params, grads, learning_rate, momentum):
        updates = []
        for n, (param, grad) in enumerate(zip(params, grads)):
            memory = self.memory_[n]
            updates.append((param, param - learning_rate * grad))
            updates.append((memory, momentum * memory + (1. - momentum) * grad))
        return updates


class sgd_nesterov(object):
    """
    SGD with nesterov momentum

    Based on example from Yann D.

    See Formula 7 from
    Advances in Optimizing Recurrent Neural Networks
    Y. Benio, N. Boulanger-Lewandowski, R. Pascanu
    """
    def __init__(self, params):
        self.memory_ = [theano.shared(np.zeros_like(p.get_value()))
                        for p in params]

    def updates(self, params, grads, learning_rate, momentum):
        updates = []
        for n, (param, grad) in enumerate(zip(params, grads)):
            memory = self.memory_[n]
            update = momentum * memory - learning_rate * grad
            update2 = momentum * momentum * memory - (
                1 + momentum) * learning_rate * grad
            updates.append((memory, update))
            updates.append((param, param + update2))
        return updates


class rmsprop(object):
    """
    RMSProp with nesterov momentum and gradient rescaling
    """
    def __init__(self, params):
        self.memory_ = [theano.shared(np.zeros_like(p.get_value()))
                        for p in params]
        self.squared_memory_ = [theano.shared(np.zeros_like(p.get_value()))
                                for p in params]
        self.momentum_memory_ = [theano.shared(np.zeros_like(p.get_value()))
                                 for p in params]

    def updates(self, params, grads, learning_rate, momentum, rescale=5.):
        grad_norm = tensor.sqrt(sum(map(lambda x: tensor.sqr(x).sum(), grads)))
        scaling_num = rescale
        scaling_den = tensor.maximum(rescale, grad_norm)
        scaling = scaling_num / scaling_den
        # constants, from AG "Generating Sequences with Recurrent Neural
        # Networks"
        decay = 0.95
        minimum_grad = 1E-4
        updates = []
        for n, (param, grad) in enumerate(zip(params, grads)):
            grad *= scaling
            memory = self.memory_[n]
            squared_memory = self.squared_memory_[n]
            momentum_memory = self.momentum_memory_[n]
            grad_gi = decay * memory + (1 - decay) * grad
            decayed_ni = decay * squared_memory + (1 - decay) * grad ** 2
            grad_scaled = grad / tensor.sqrt(
                decayed_ni - grad_gi ** 2 + minimum_grad)
            update = momentum * momentum_memory - learning_rate * grad_scaled
            update2 = momentum * momentum * momentum_memory - (
                1 + momentum) * learning_rate * grad_scaled
            updates.append((memory, grad_gi))
            updates.append((squared_memory, decayed_ni))
            updates.append((momentum_memory, update))
            updates.append((param, param + update2))
        return updates


class adagrad(object):
    """
    Adagrad optimizer
    """
    def __init__(self, params):
        self.memory_ = [theano.shared(np.zeros_like(p.get_value()))
                        for p in params]

    def updates(self, params, grads, learning_rate, eps=1E-8):
        updates = []
        for n, (param, grad) in enumerate(zip(params, grads)):
            memory = self.memory_[n]
            m_t = memory + grad ** 2
            g_t = grad / (eps + tensor.sqrt(m_t))
            p_t = param - learning_rate * g_t
            updates.append((memory, m_t))
            updates.append((param, p_t))
        return updates


class adadelta(object):
    """
    An adaptive learning rate optimizer

    For more information, see:
    Matthew D. Zeiler, "ADADELTA: An Adaptive Learning Rate Method"
    arXiv:1212.5701.
    """
    def __init__(self, params):
        self.running_up2_ = [theano.shared(np.zeros_like(p.get_value()))
                             for p in params]
        self.running_grads2_ = [theano.shared(np.zeros_like(p.get_value()))
                                for p in params]
        self.previous_grads_ = [theano.shared(np.zeros_like(p.get_value()))
                                for p in params]

    def updates(self, params, grads, running_grad_decay=0.95,
                running_up_decay=0.95, eps=1E-6):
        updates = []
        for n, (param, grad) in enumerate(zip(params, grads)):
            running_grad2 = self.running_grads2_[n]
            running_up2 = self.running_up2_[n]
            previous_grad = self.previous_grads_[n]
            rg2up = running_grad_decay * running_grad2 + (
                1. - running_grad_decay) * (grad ** 2)
            updir = -tensor.sqrt(running_up2 + eps) / tensor.sqrt(
                running_grad2 + eps) * previous_grad
            ru2up = running_up_decay * running_up2 + (
                1. - running_up_decay) * (updir ** 2)
            updates.append((previous_grad, grad))
            updates.append((running_grad2, rg2up))
            updates.append((running_up2, ru2up))
            updates.append((param, param + updir))
        return updates


class adam(object):
    """
    Adam optimizer

    Based on implementation from @NewMu / Alex Radford
    """
    def __init__(self, params):
        self.memory_ = [theano.shared(np.zeros_like(p.get_value()))
                        for p in params]
        self.velocity_ = [theano.shared(np.zeros_like(p.get_value()))
                          for p in params]
        self.itr_ = theano.shared(np.array(0.).astype(theano.config.floatX))

    def updates(self, params, grads, learning_rate, b1=0.1, b2=0.001, eps=1E-8):
        updates = []
        itr = self.itr_
        i_t = itr + 1.
        fix1 = 1. - (1. - b1) ** i_t
        fix2 = 1. - (1. - b2) ** i_t
        lr_t = learning_rate * (tensor.sqrt(fix2) / fix1)
        for n, (param, grad) in enumerate(zip(params, grads)):
            memory = self.memory_[n]
            velocity = self.velocity_[n]
            m_t = (b1 * grad) + ((1. - b1) * memory)
            v_t = (b2 * tensor.sqr(grad)) + ((1. - b2) * velocity)
            g_t = m_t / (tensor.sqrt(v_t) + eps)
            p_t = param - (lr_t * g_t)
            updates.append((memory, m_t))
            updates.append((velocity, v_t))
            updates.append((param, p_t))
        updates.append((itr, i_t))
        return updates
