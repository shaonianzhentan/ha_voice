

class HaVoicePanel extends HTMLElement {
    constructor() {
        super()
        const shadow = this.attachShadow({ mode: 'open' });
        const div = document.createElement('ha-card');
        div.className = 'ha-voice-panel'
        div.innerHTML = `
        <div class="card-header">
            <a class="name">
                <ha-icon icon="mdi:microphone"></ha-icon> 语音小助手
            </a>
			<ha-switch></ha-switch>
        </div>
        
        <div class="card-content">
            <hr />
            <div class="row">
                <div>是否支持Google服务</div>
                <div class="is-google">--</div>
            </div>
            <div class="row">
                <div>是否支持HTTPS</div>
                <div class="is-https">--</div>
            </div>
            <div class="row">
                <div>是否localhost域名</div>
                <div class="is-localhost">是</div>
            </div>
            <hr />
            点击标题【语音小助手】，赶紧体验一下吧
			<input type="text" placeholder="语音文字命令" class="txtCmd" />
			<div class="cfg-cmd">
			</div>
        </div>
        <iframe class="hide"></iframe>`
        shadow.appendChild(div)

        const style = document.createElement('style')
        style.textContent = `
            .ha-voice-panel{    
                position: relative;
                width: 100%;
                overflow: hidden;
                z-index: 0;}
            .row{display:flex;justify-content: space-between;}
            .ha-voice-panel iframe{width:100%;min-height:400px;border:none;margin-bottom: -4px;}
            .card-content{color:gray;line-height:25px;}
            .card-header{display:flex;justify-content: space-between;}
			.card-header .name{color: var(--material-primary-color);cursor:pointer;text-decoration:none;}
            .hide{display:none;}
            .txtCmd{width:100%;padding:10px;box-sizing: border-box;margin:8px 0;}
			.cfg-cmd span{margin-right:10px;color: var(--material-primary-color);cursor:pointer;}
        `
        shadow.appendChild(style);
        this.shadow = shadow
        const $ha = this.shadow.querySelector.bind(this.shadow)

        // 发送文字命令
        let txtCmd = shadow.querySelector('.txtCmd')
        txtCmd.onkeyup = async (event) => {
            if (event.keyCode === 13) {
                console.log(this.hass)
                let text = txtCmd.value.trim()
                txtCmd.value = ''
                this.send(text)
            }
        }

        $ha('ha-switch').onchange = (event) => {
            let ele = event.path[0]
            let iframe = $ha('iframe')
            let card = $ha('.card-content')

            if (ele.checked) {
                if (!iframe.src) {
                    iframe.src = $ha('.card-header .name').dataset['link']
                }
                iframe.classList.remove('hide')
                card.classList.add('hide')
            } else {
                iframe.classList.add('hide')
                card.classList.remove('hide')
            }
        }

    }

    toast(message) {
        document.querySelector('home-assistant').dispatchEvent(new CustomEvent("hass-notification", { detail: { message } }))
    }

    send(text) {
        this.hass.callService('ha_voice', 'process', { text })
        this.toast(`【${text}】发送成功`)
    }

    google() {
        return new Promise((resolve, reject) => {
            const controller = new AbortController();
            let signal = controller.signal;
            // 判断是否Chrome浏览器
            let isChrome = speechSynthesis.getVoices().some(ele => ele.name.includes('Google'))
            if(!isChrome){
                reject()
            }
            fetch('https://www.google.com/gen_204', { mode: 'no-cors', signal }).then(res => {
                resolve()
            })
            setTimeout(() => {
                controller.abort();
                reject()
            }, 2000)
        })
    }

    get hass() {
        return this._hass
    }

    set hass(hass) {
        // console.log(hass)
        this._hass = hass
        let { states } = hass
        let yy = states['weblink.yu_yin_xiao_zhu_shou']
        if (yy) {
            if (this.loading) return;
            this.loading = true
            const $ha = this.shadow.querySelector.bind(this.shadow)
            let headerLink = $ha('.card-header .name')
            // 浏览器检测
            let ck = {
                isHttps: location.protocol === 'https:',
                isLocalhost: location.hostname === 'localhost'
            }
            $ha('.is-https').textContent = ck.isHttps ? '支持' : '不支持'
            $ha('.is-localhost').textContent = ck.isLocalhost ? '支持' : '不支持'
            headerLink.dataset['link'] = yy.state
            // 判断是否支持本地使用
            if (ck.isHttps || ck.isLocalhost) {
                headerLink.removeAttribute('target')
                headerLink.removeAttribute('href')
                headerLink.onclick = () => {
                    $ha('.card-content').classList.add('hide')
                    let iframe = $ha('iframe')
                    iframe.src = yy.state
                    iframe.classList.remove('hide')
                    $ha('ha-switch').checked = true
                }
            } else {
                headerLink.setAttribute('target', '_blank')
                headerLink.setAttribute('href', yy.state)
                $ha('ha-switch').classList.add('hide')
            }
            // 检测是否支持Google服务
            this.google().then(() => {
                $ha('.is-google').textContent = '支持'
            }).catch(() => {
                $ha('.is-google').textContent = '不支持'
            }).finally(() => {
                setTimeout(() => {
                    this.loading = false
                }, 11000)
            })
        }
    }

    setConfig(config) {
        this.config = config || {};
        // 
        let { cmd } = this.config
        if (Array.isArray(cmd)) {
            let arr = cmd.map(ele => {
                return `<span>${ele}</span>`
            })
            let cfgcmd = this.shadow.querySelector('.cfg-cmd')
            cfgcmd.innerHTML = arr.join('')
            cfgcmd.onclick = (event) => {
                let text = event.path[0].innerText
                this.send(text)
            }
        }
    }

    getCardSize() {
        return 3
    }
}

customElements.define('ha-voice-panel', HaVoicePanel);