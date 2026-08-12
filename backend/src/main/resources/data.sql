INSERT INTO sys_user (id, username, password_hash, nickname, avatar_url, role, status)
VALUES
  (1, 'admin', '{noop}123456', '管理员', 'avatar-compass', 'ADMIN', 1),
  (2, 'user', '{noop}123456', '旅行者', 'avatar-backpack', 'USER', 1)
ON DUPLICATE KEY UPDATE
  password_hash = VALUES(password_hash),
  nickname = VALUES(nickname),
  avatar_url = VALUES(avatar_url),
  role = VALUES(role),
  status = VALUES(status);

INSERT INTO city (id, name, province, summary, best_season, image_url, sort_order)
VALUES
  (1, '成都', '四川', '火锅沸腾、熊猫打滚的慢生活之城，市井烟火与古蜀文化交融，三天不够吃。', '3-6月、9-11月', 'oneclick-trip-assets/chengdu-destination.png', 1),
  (2, '杭州', '浙江', '西湖烟雨、灵隐钟声、龙井茶山，一座适合慢走慢品的江南城市。', '3-5月、9-10月', 'oneclick-trip-assets/hangzhou-west-lake.png', 2),
  (3, '西安', '陕西', '十三朝古都，兵马俑的震撼、城墙的落日、回民街的烟火，历史与碳水在此交汇。', '3-5月、9-11月', 'oneclick-trip-assets/xian-city-wall.png', 3),
  (4, '大理', '云南', '苍山雪、洱海月、古城风、白族味，适合把时间放慢、把心情放空的度假地。', '全年适合，3-5月更舒适', 'oneclick-trip-assets/dali-erhai.png', 4)
ON DUPLICATE KEY UPDATE
  name = VALUES(name), province = VALUES(province), summary = VALUES(summary),
  best_season = VALUES(best_season), image_url = VALUES(image_url), sort_order = VALUES(sort_order);

-- ==================== 成都 景点 1-8 ====================
INSERT INTO scenic_spot (id, city_id, name, address, summary, ticket_price, open_time, play_hours, rating, tags, image_url, sort_order) VALUES
  (1, 1, '成都大熊猫繁育研究基地', '成都市成华区熊猫大道1375号', '看花花和萌团子，建议7:30开园就冲，上午熊猫更活跃。', 55, '07:30-18:00', 3.5, 4.8, '亲子,必去,轻松', 'oneclick-trip-assets/chengdu-panda-base.png', 1),
  (2, 1, '宽窄巷子', '成都市青羊区长顺街附近', '清代古街院落群，散步拍照感受川西民居，紧邻奎星楼小吃街。', 0, '全天开放', 2.0, 4.5, '街区,美食,拍照', 'oneclick-trip-assets/chengdu-kuanzhai-alley.png', 2),
  (3, 1, '武侯祠·锦里', '成都市武侯区武侯祠大街231号', '三国文化圣地，红墙竹影超出片；隔壁锦里夜景绝美，灯笼一亮直接穿越。', 50, '09:00-18:00（锦里全天开放）', 3.0, 4.7, '三国,历史,夜景', 'oneclick-trip-assets/chengdu-wuhou-temple.png', 3),
  (4, 1, '杜甫草堂', '成都市青羊区青华路37号', '诗圣流落成都时的住处，茅屋竹林文人氛围浓厚，适合半日安静游览。', 60, '09:00-18:00', 2.5, 4.6, '人文,历史,安静', 'oneclick-trip-assets/chengdu-dufu-cottage.png', 4),
  (5, 1, '春熙路·太古里', '成都市锦江区春熙路', '爬墙熊猫打卡地，超百家国际品牌与本地潮牌聚集，IFS楼顶视野绝佳。', 0, '全天开放', 2.5, 4.7, '购物,打卡,都市', 'oneclick-trip-assets/chengdu-chunxi-road.png', 5),
  (6, 1, '文殊院', '成都市青羊区文殊院街66号', '香火超旺的千年古寺，红墙拍照出片率极高，可吃斋饭喝盖碗茶。', 0, '08:00-17:00', 2.0, 4.6, '寺院,人文,安静', 'oneclick-trip-assets/chengdu-wenshu-temple.png', 6),
  (7, 1, '东郊记忆', '成都市成华区建设南支路4号', '旧工厂改造的文艺园区，工业风+漫展音乐节，傍晚光线更柔和。', 0, '全天开放', 2.0, 4.4, '文艺,拍照,下午茶', 'oneclick-trip-assets/chengdu-east-suburb.png', 7),
  (8, 1, '都江堰', '成都市都江堰市公园路', '千年水利奇迹，从秦堰楼俯瞰全景最震撼，离堆公园与二王庙不可错过。', 80, '08:00-17:30', 5.0, 4.8, '世界遗产,工程奇观,一日游', 'oneclick-trip-assets/chengdu-dujiangyan.png', 8)
ON DUPLICATE KEY UPDATE
  city_id = VALUES(city_id), name = VALUES(name), summary = VALUES(summary),
  ticket_price = VALUES(ticket_price), play_hours = VALUES(play_hours), rating = VALUES(rating),
  tags = VALUES(tags), image_url = VALUES(image_url), sort_order = VALUES(sort_order);

-- ==================== 成都 美食 1-7 ====================
INSERT INTO food (id, city_id, name, category, summary, recommended_area, avg_price, image_url, sort_order) VALUES
  (1, 1, '牛油火锅', '晚餐首选', '正宗牛油锅底，毛肚七上八下、鸭肠挂汤，配一碗冰粉收尾，人均80-120元。', '春熙路、玉林、建设路', 100, 'oneclick-trip-assets/chengdu-food-hotpot.png', 1),
  (2, 1, '担担面与冰粉', '小吃组合', '手工碱水面配肉臊芽菜红油，吃完再来一碗手搓冰粉解辣，景点间隙快速补能。', '宽窄巷子、奎星楼街', 30, 'oneclick-trip-assets/chengdu-food-snacks.png', 2),
  (3, 1, '麻辣兔头', '成都名片', '淋满辣椒油和花生碎，越啃越香，成都人一年啃掉几千万只。', '双流、玉林、各大卤菜摊', 15, 'oneclick-trip-assets/chengdu-spicy-rabbit.png', 3),
  (4, 1, '蛋烘糕', '街头甜品', '面糊在铜模里鼓起，边缘焦脆内馅任选——奶油、肉松、芝麻糖随便搭配。', '街头巷尾、建设路', 8, 'oneclick-trip-assets/chengdu-egg-cake.png', 4),
  (5, 1, '甜水面', '面食经典', '面条粗硬筋道，甜辣酱汁浓郁，嚼劲十足，一根面能吃出层次感。', '文殊院、洞子口', 12, 'oneclick-trip-assets/chengdu-sweet-noodle.png', 5),
  (6, 1, '钵钵鸡', '冷串天花板', '红油或藤椒汤底，鸡肉、毛肚、藕片浸泡入味，香辣不烫嘴。', '春熙路、玉林', 35, 'oneclick-trip-assets/chengdu-bobo-chicken.png', 6),
  (7, 1, '蹄花汤', '深夜暖胃', '猪蹄炖六小时一夹脱骨，汤白如奶配蘸水，凌晨两点照样排队。', '人民公园、玉林', 40, 'oneclick-trip-assets/chengdu-pig-trotter.png', 7)
ON DUPLICATE KEY UPDATE
  city_id = VALUES(city_id), name = VALUES(name), category = VALUES(category),
  summary = VALUES(summary), recommended_area = VALUES(recommended_area),
  avg_price = VALUES(avg_price), image_url = VALUES(image_url), sort_order = VALUES(sort_order);

-- ==================== 杭州 景点 9-14 ====================
INSERT INTO scenic_spot (id, city_id, name, address, summary, ticket_price, open_time, play_hours, rating, tags, image_url, sort_order) VALUES
  (9, 2, '西湖', '杭州市西湖区', '断桥残雪、白堤、苏堤、花港观鱼串成一条经典环湖线，骑行或步行慢游最佳。', 0, '全天开放', 4.0, 4.9, '湖景,散步,拍照,必去', 'oneclick-trip-assets/hangzhou-west-lake.png', 1),
  (10, 2, '灵隐寺', '杭州市西湖区法云弄1号', '千年古刹香火鼎盛，飞来峰石刻精美，建议上午前往人少清静。', 75, '07:00-18:00', 3.0, 4.7, '寺院,人文,必去', 'oneclick-trip-assets/hangzhou-lingyin-temple.png', 2),
  (11, 2, '雷峰塔', '杭州市西湖区南山路15号', '傍晚登塔看西湖日落全景，塔身金光闪闪，与保俶塔隔湖相望。', 40, '08:00-17:30', 2.0, 4.6, '湖景,日落,地标', 'oneclick-trip-assets/hangzhou-leifeng-pagoda.png', 3),
  (12, 2, '龙井村·梅家坞', '杭州市西湖区龙井路', '漫步千亩茶园，到茶农家里品一杯现炒龙井，满眼翠绿满口清香。', 0, '全天开放', 3.0, 4.7, '茶园,品茶,拍照', 'oneclick-trip-assets/hangzhou-longjing-village.png', 4),
  (13, 2, '河坊街·南宋御街', '杭州市上城区河坊街', '南宋古街风情，定胜糕、葱包烩、藕粉边走边吃，晚上灯笼亮起更有韵味。', 0, '全天开放', 2.5, 4.4, '街区,美食,夜游', 'oneclick-trip-assets/hangzhou-hefang-street.png', 5),
  (14, 2, '西溪湿地', '杭州市西湖区天目山路518号', '坐摇橹船穿行芦苇水道，白鹭惊飞，是城市里的天然氧吧。', 80, '08:00-17:00', 4.0, 4.5, '湿地,游船,自然', 'oneclick-trip-assets/hangzhou-xixi-wetland.png', 6)
ON DUPLICATE KEY UPDATE
  city_id = VALUES(city_id), name = VALUES(name), summary = VALUES(summary),
  ticket_price = VALUES(ticket_price), play_hours = VALUES(play_hours), rating = VALUES(rating),
  tags = VALUES(tags), image_url = VALUES(image_url), sort_order = VALUES(sort_order);

-- ==================== 杭州 美食 8-13 ====================
INSERT INTO food (id, city_id, name, category, summary, recommended_area, avg_price, image_url, sort_order) VALUES
  (8, 2, '龙井虾仁', '杭帮经典', '龙井新茶现烹鲜活河虾仁，茶香虾鲜入口清爽，春天的杭州味。', '湖滨、龙井村', 88, 'oneclick-trip-assets/hangzhou-longjing-snacks.png', 1),
  (9, 2, '片儿川', '本地面食', '雪菜、笋片、瘦肉片煮出的杭州第一面，汤头鲜美，奎元馆的最经典。', '湖滨、武林、奎元馆', 25, 'oneclick-trip-assets/hangzhou-pianerchuan.png', 2),
  (10, 2, '东坡肉', '宴客大菜', '五花肉慢炖至肥而不腻、入口即化，酱色红亮甜咸适中，楼外楼名菜。', '楼外楼、外婆家', 68, 'oneclick-trip-assets/hangzhou-dongpo-pork.png', 3),
  (11, 2, '西湖醋鱼', '经典名菜', '草鱼现杀糖醋烹制，鱼肉嫩滑酸甜开胃，用筷子一拨即散。', '楼外楼、知味观', 78, 'oneclick-trip-assets/hangzhou-westlake-fish.png', 4),
  (12, 2, '葱包烩', '街头小吃', '薄饼裹油条压烤至焦脆，刷甜面酱或辣酱，每份10-15元边走边吃。', '河坊街、中山南路', 12, 'oneclick-trip-assets/hangzhou-congbaohui.png', 5),
  (13, 2, '定胜糕', '传统甜点', '糯米粉蒸制粉红小糕，豆沙馅绵密，河坊街随处可买，寓意好。', '河坊街', 10, 'oneclick-trip-assets/hangzhou-dingsheng-cake.png', 6)
ON DUPLICATE KEY UPDATE
  city_id = VALUES(city_id), name = VALUES(name), category = VALUES(category),
  summary = VALUES(summary), recommended_area = VALUES(recommended_area),
  avg_price = VALUES(avg_price), image_url = VALUES(image_url), sort_order = VALUES(sort_order);

-- ==================== 西安 景点 15-20 ====================
INSERT INTO scenic_spot (id, city_id, name, address, summary, ticket_price, open_time, play_hours, rating, tags, image_url, sort_order) VALUES
  (15, 3, '秦始皇兵马俑', '西安市临潼区秦陵北路', '世界第八大奇迹，一号坑军阵震撼人心，建议请官方讲解才能看懂门道。', 120, '08:30-18:00', 4.0, 4.9, '历史,必去,世界遗产', 'oneclick-trip-assets/xian-terracotta-army.png', 1),
  (16, 3, '西安城墙', '西安市碑林区南大街', '永宁门登城、傍晚骑行看落日，俯瞰古城内外千年对比。', 54, '08:00-22:00', 2.5, 4.8, '骑行,夜景,地标', 'oneclick-trip-assets/xian-city-wall.png', 2),
  (17, 3, '大雁塔·大唐不夜城', '西安市雁塔区慈恩路', '白天看大雁塔音乐喷泉，晚上不夜城灯光亮起，李白对诗、不倒翁表演免费看。', 0, '全天开放（不夜城19:30亮灯）', 3.0, 4.7, '夜景,免费,文化', 'oneclick-trip-assets/xian-datang-mall.png', 3),
  (18, 3, '钟楼·鼓楼', '西安市碑林区东西南北大街交汇', '西安正中心，登楼看中轴线贯通的古城格局，夜景金碧辉煌。', 30, '08:30-21:00', 1.5, 4.5, '地标,夜景,打卡', 'oneclick-trip-assets/xian-bell-drum-tower.png', 4),
  (19, 3, '回民街·洒金桥', '西安市莲湖区回民街', '回民街主街拍照打卡，往里走洒金桥、大皮院才是本地人真正吃小吃的地方。', 0, '全天开放', 2.5, 4.4, '美食,街区,市井', 'oneclick-trip-assets/xian-muslim-street.png', 5),
  (20, 3, '陕西历史博物馆', '西安市雁塔区小寨东路91号', '华夏珍宝库，从商周青铜器到唐代金银器，免费但需提前3天抢票。', 0, '08:30-17:30（周一闭馆）', 3.0, 4.8, '历史,免费,必去', 'oneclick-trip-assets/xian-history-museum.png', 6)
ON DUPLICATE KEY UPDATE
  city_id = VALUES(city_id), name = VALUES(name), summary = VALUES(summary),
  ticket_price = VALUES(ticket_price), play_hours = VALUES(play_hours), rating = VALUES(rating),
  tags = VALUES(tags), image_url = VALUES(image_url), sort_order = VALUES(sort_order);

-- ==================== 西安 美食 14-20 ====================
INSERT INTO food (id, city_id, name, category, summary, recommended_area, avg_price, image_url, sort_order) VALUES
  (14, 3, '肉夹馍', '碳水之王', '腊汁肉剁碎夹进现烤白吉馍，外皮酥脆掉渣肉汁饱满，子午路张记最地道。', '钟楼、子午路、洒金桥', 12, 'oneclick-trip-assets/xian-roujiamo-liangpi.png', 1),
  (15, 3, '羊肉泡馍', '西安灵魂', '自己掰馍越小越入味，配糖蒜和辣酱，汤浓肉烂一碗顶饱半天。', '钟楼、回民街、洒金桥', 45, 'oneclick-trip-assets/xian-yangrou-paomo.png', 2),
  (16, 3, 'Biangbiang面', '面食招牌', '三合一裤带面宽如皮带，油泼辣子滋啦一响，人均20吃到撑。', '钟楼小区、爱骅裤带面馆', 20, 'oneclick-trip-assets/xian-biangbiang-noodle.png', 3),
  (17, 3, '贾三灌汤包', '回民经典', '皮薄如纸一咬汤汁四溢，牛肉或羊肉馅，蘸醋姜丝提鲜。', '回民街', 28, 'oneclick-trip-assets/xian-soup-dumpling.png', 4),
  (18, 3, '甑糕', '甜蜜早点', '糯米和蜜枣层层堆叠蒸制，甜糯拉丝，洒金桥胖子甑糕早起才抢得到。', '洒金桥、早市', 10, 'oneclick-trip-assets/xian-zenggao.png', 5),
  (19, 3, '水盆羊肉', '汤浓肉烂', '清汤羊肉配月牙饼，汤鲜肉烂暖胃舒服，澄城风味最正。', '洒金桥、北广济街', 35, 'oneclick-trip-assets/xian-mutton-soup.png', 6),
  (20, 3, '麻酱凉皮', '夏日必吃', '陕西凉皮筋道爽滑，麻酱蒜汁辣油一拌，酸辣开胃消暑利器。', '回民街、各大面馆', 10, 'oneclick-trip-assets/xian-sesame-noodle.png', 7)
ON DUPLICATE KEY UPDATE
  city_id = VALUES(city_id), name = VALUES(name), category = VALUES(category),
  summary = VALUES(summary), recommended_area = VALUES(recommended_area),
  avg_price = VALUES(avg_price), image_url = VALUES(image_url), sort_order = VALUES(sort_order);

-- ==================== 大理 景点 21-26 ====================
INSERT INTO scenic_spot (id, city_id, name, address, summary, ticket_price, open_time, play_hours, rating, tags, image_url, sort_order) VALUES
  (21, 4, '洱海生态廊道', '大理市洱海沿线', '海西46公里骑行绿道，从才村到S弯再到喜洲，一步一景，日出日落都美到窒息。', 0, '全天开放', 5.0, 4.9, '湖景,骑行,日出,必去', 'oneclick-trip-assets/dali-erhai.png', 1),
  (22, 4, '大理古城', '大理市一塔路42号', '人民路的民谣酒馆、复兴路的烤乳扇、南门的篝火晚会，白天夜晚各有精彩。', 0, '全天开放', 3.0, 4.6, '古城,美食,夜生活', 'oneclick-trip-assets/dali-ancient-city.png', 2),
  (23, 4, '喜洲古镇', '大理市喜洲镇', '白族古民居群与稻田交错，转角楼和黄墙是经典机位，喜洲粑粑现烤最香。', 0, '全天开放', 3.0, 4.7, '古镇,稻田,拍照', 'oneclick-trip-assets/dali-xizhou-town.png', 3),
  (24, 4, '双廊古镇', '大理市双廊镇', '洱海最美岸线，玉几岛俯瞰整片湖景，海景咖啡和民宿密度极高。', 0, '全天开放', 4.0, 4.7, '湖景,海景,度假', 'oneclick-trip-assets/dali-erhai.png', 4),
  (25, 4, '崇圣寺三塔', '大理市崇圣寺', '大理地标级古建筑，唐代三塔与苍山相映，"三塔倒影"是经典摄影机位。', 75, '08:00-18:00', 2.5, 4.5, '地标,历史,人文', 'oneclick-trip-assets/dali-three-pagodas.png', 5),
  (26, 4, '苍山·寂照庵', '大理市苍山', '乘感通索道上山观洱海全景，寂照庵满院多肉超禅意，素斋20元/位值得一试。', 120, '08:30-17:00', 4.0, 4.6, '山景,寺院,素斋', 'oneclick-trip-assets/dali-cangshan.png', 6)
ON DUPLICATE KEY UPDATE
  city_id = VALUES(city_id), name = VALUES(name), summary = VALUES(summary),
  ticket_price = VALUES(ticket_price), play_hours = VALUES(play_hours), rating = VALUES(rating),
  tags = VALUES(tags), image_url = VALUES(image_url), sort_order = VALUES(sort_order);

-- ==================== 大理 美食 21-26 ====================
INSERT INTO food (id, city_id, name, category, summary, recommended_area, avg_price, image_url, sort_order) VALUES
  (21, 4, '野生菌火锅', '云南必吃', '雨季鲜菌现煮30分钟，鸡汤锅底涮松茸牛肝菌，喝三碗汤才算来过云南。', '大理古城、下关', 80, 'oneclick-trip-assets/dali-mushroom-hotpot.png', 1),
  (22, 4, '烤乳扇', '白族小吃', '牛奶制成薄片炭火烤至微焦，刷玫瑰酱卷起来拉丝，酸甜奶香古城随处可买。', '大理古城、喜洲', 8, 'oneclick-trip-assets/dali-rushan-flower-cake.png', 2),
  (23, 4, '喜洲破酥粑粑', '现烤首选', '甜口玫瑰红糖、咸口鲜肉葱油，炭火烤到层层起酥掉渣，10块钱一大个。', '喜洲古镇', 10, 'oneclick-trip-assets/dali-xizhou-baba.png', 3),
  (24, 4, '大理酸辣鱼', '白族家常', '洱海鲫鱼配酸木瓜炖煮，汤汁酸辣鲜香，蘸水性杨花菜一口汤一口饭。', '古城餐馆、才村', 55, 'oneclick-trip-assets/dali-sour-fish.png', 4),
  (25, 4, '凉鸡米线', '夏日必吃', '手撕鸡肉配酸辣酱汁拌本地米线，酸甜微辣清凉开胃，古城路边摊最地道。', '大理古城', 12, 'oneclick-trip-assets/dali-cold-noodle.png', 5),
  (26, 4, '白族石板烧', '烟火硬菜', '大理石板上现烤五花肉、牛肉和包浆豆腐，外焦里嫩滋滋冒油，配蘸水绝了。', '大理古城南门', 60, 'oneclick-trip-assets/dali-stone-grill.png', 6)
ON DUPLICATE KEY UPDATE
  city_id = VALUES(city_id), name = VALUES(name), category = VALUES(category),
  summary = VALUES(summary), recommended_area = VALUES(recommended_area),
  avg_price = VALUES(avg_price), image_url = VALUES(image_url), sort_order = VALUES(sort_order);

-- ==================== 酒店 ====================
INSERT INTO hotel (id, city_id, name, area, summary, price_level, avg_price, rating) VALUES
  (1, 1, '春熙路舒适酒店', '春熙路/太古里', '地铁2号线直达，去熊猫基地和春熙路都顺路，周边美食密集。', 'MEDIUM', 360, 4.6),
  (2, 1, '宽窄巷子精品民宿', '宽窄巷子', '老街区院落改造，晚上散步出门就是小吃和茶社。', 'MEDIUM', 420, 4.5),
  (3, 1, '高新区商务酒店', '天府三街/世纪城', '环境安静性价比高，适合预算紧凑的行程。', 'LOW', 220, 4.3),
  (4, 2, '湖滨轻奢酒店', '西湖湖滨', '步行到西湖5分钟，湖景房看日出，适合犒劳自己的旅程。', 'HIGH', 620, 4.7),
  (5, 2, '龙井村茶园民宿', '龙井村/满觉陇', '宿在茶园中，清晨被鸟鸣唤醒，后院就是茶山。', 'MEDIUM', 380, 4.6),
  (6, 2, '河坊街快捷酒店', '南宋御街/河坊街', '出门就是古街夜市，经济实惠适合学生党。', 'LOW', 180, 4.2),
  (7, 3, '钟楼精选酒店', '钟楼/回民街', '西安正中心，步行到钟楼3分钟、回民街5分钟，午夜饿了走几步就解决。', 'MEDIUM', 330, 4.5),
  (8, 3, '南门城墙精品酒店', '永宁门/南门', '窗外就是古城墙夜景，清晨上城墙散步后回来吃早餐。', 'HIGH', 520, 4.6),
  (9, 3, '大雁塔快捷酒店', '大雁塔/小寨', '靠近陕历博和大唐不夜城，晚上逛完不夜城走回酒店。', 'MEDIUM', 280, 4.3),
  (10, 4, '洱海边度假民宿', '洱海生态廊道/才村', '推窗见洱海，适合慢节奏度假和看日出，房间里就能拍苍山洱海。', 'MEDIUM', 460, 4.6),
  (11, 4, '古城庭院客栈', '大理古城人民路', '白族院落改的客栈，院里有树有花有猫，出门就是人民路的民谣和夜宵。', 'MEDIUM', 320, 4.5),
  (12, 4, '双廊海景民宿', '双廊古镇', '一线海景大落地窗，躺在浴缸里看洱海落日，贵但值得一晚。', 'HIGH', 680, 4.7)
ON DUPLICATE KEY UPDATE
  city_id = VALUES(city_id), name = VALUES(name), area = VALUES(area), summary = VALUES(summary),
  price_level = VALUES(price_level), avg_price = VALUES(avg_price), rating = VALUES(rating);

-- ==================== 精选行程模板 ====================
INSERT INTO trip_template (id, city_id, title, days, budget_level, pace, summary, cover_url) VALUES
  -- 成都 3 款
  (1, 1, '成都3日经典线：熊猫·古街·火锅', 3, 'MEDIUM', 'RELAXED',
   'Day1 上午春熙路IFS打卡爬墙熊猫→太古里逛川西院落与现代设计的碰撞→中午在太古里周边吃钵钵鸡→下午人民公园鹤鸣茶社喝盖碗茶→傍晚宽窄巷子散步拍照→晚餐奎星楼街吃串串香。'
   'Day2 早上7:30冲熊猫基地看花花（上午熊猫最活跃！）→中午回市区吃担担面→下午文殊院求签祈福、红墙拍照→晚上建设路夜市：烤苕皮、锅巴土豆、蛋烘糕一路吃过去。'
   'Day3 上午武侯祠感受三国→中午锦里古街逛吃→下午杜甫草堂安静散步→傍晚玉林路找家社区火锅涮毛肚鸭肠，配一碗冰粉完美收官。三天把成都的萌、慢、辣一次收齐。',
   'oneclick-trip-assets/chengdu-destination.png'),

  (5, 1, '成都2日吃货专线：以吃之名', 2, 'LOW', 'RELAXED',
   'Day1 睡到自然醒→文殊院洞子口吃甜水面和钟水饺→宽窄巷子散步消食→下午春熙路逛街→晚餐牛油火锅大餐（毛肚、鸭肠、嫩牛肉安排上）→深夜玉林路蹄花汤暖胃收尾。'
   'Day2 早上建设路吃蛋烘糕和糖油果子→熊猫基地看花花→中午回奎星楼街吃冒菜配冰粉→下午人民公园喝茶消食→晚上吃钵钵鸡冷串配甜水面→打包兔头当夜宵。两天人均不过500，把成都小吃地图画个圈。',
   'oneclick-trip-assets/chengdu-food-hotpot.png'),

  (6, 1, '成都4日慢享线：市区+都江堰', 4, 'MEDIUM', 'RELAXED',
   'Day1 春熙路→太古里→大慈寺→方所书店→晚餐太古里周边川菜。Day2 熊猫基地→文殊院→建设路夜市。Day3 早班城际列车到都江堰→秦堰楼俯瞰全景→二王庙→离堆公园→南桥午餐吃河鲜→下午返回市区逛东郊记忆。'
   'Day4 武侯祠·锦里→杜甫草堂→最后在玉林吃一顿社区老火锅，买两包火锅底料当伴手礼。第四天不赶路，前三天没去够的地方可以补。',
   'oneclick-trip-assets/chengdu-dujiangyan.png'),

  -- 杭州 2 款
  (2, 2, '杭州2日西湖精华', 2, 'MEDIUM', 'RELAXED',
   'Day1 清晨断桥残雪出发→白堤走到孤山→西泠印社→乘船上三潭印月（1元纸币同款背景）→中午湖滨外婆家吃东坡肉和龙井虾仁→下午苏堤骑行到花港观鱼→傍晚雷峰塔看西湖日落→晚上河坊街逛吃：定胜糕、葱包烩、藕粉。'
   'Day2 早起灵隐寺（7点前人少清静）→飞来峰石刻→永福寺喝杯"慈杯"咖啡→中午天竺路吃素面→下午龙井村漫步茶园、到茶农家喝现炒龙井→晚餐知味观来一碗片儿川返程。两天环湖一圈、进山一趟，杭州的湖光与禅意都收齐了。',
   'oneclick-trip-assets/hangzhou-west-lake.png'),

  (7, 2, '杭州3日禅茶慢旅', 3, 'MEDIUM', 'RELAXED',
   'Day1 西湖经典环湖（断桥→白堤→孤山→三潭印月→苏堤→雷峰塔日落）→晚餐杭帮菜。Day2 灵隐寺→永福寺→韬光寺→龙井村品茶→梅家坞茶园漫步→晚餐片儿川与葱包烩。'
   'Day3 西溪湿地坐摇橹船穿行芦苇水道→中午河坊街逛吃→下午南宋御街买伴手礼→在定胜糕的甜香里结束杭州。三天分别给了湖、山、湿地，节奏刚好不赶也不空。',
   'oneclick-trip-assets/hangzhou-longjing-village.png'),

  -- 西安 2 款
  (3, 3, '西安3日穿越之旅', 3, 'MEDIUM', 'COMPACT',
   'Day1 上午兵马俑（请官方讲解，一号坑最震撼）→中午吃Biangbiang面→下午回市区永宁门登城墙、租自行车骑行看日落→晚上钟楼亮灯拍照→回民街洒金桥吃羊肉泡馍。'
   'Day2 上午陕西历史博物馆（提前3天抢票！）→中午赛格吃水盆羊肉→下午大雁塔→大悦城4楼观景台拍全景→晚上大唐不夜城：不倒翁表演、李白对诗、灯光秀。'
   'Day3 早起洒金桥早市吃甑糕和肉夹馍→回民街大皮院吃灌汤包→下午逛钟楼商圈→临走前再打包一份麻酱凉皮带走。三天把周秦汉唐和碳水快乐一起打包。',
   'oneclick-trip-assets/xian-city-wall.png'),

  (8, 3, '西安2日碳水朝圣：历史佐餐', 2, 'LOW', 'COMPACT',
   'Day1 早上洒金桥胖子甑糕→兵马俑（半天）→午餐Biangbiang面+肉夹馍→下午城墙骑行消食→晚餐羊肉泡馍自己掰馍→宵夜回民街烤串配冰峰汽水。'
   'Day2 早上水盆羊肉暖胃→陕历博（两小时精华）→中午灌汤包+麻酱凉皮→下午大雁塔拍照→大唐不夜城逛→晚餐葫芦头泡馍收尾。两天人均不超400，历史看了、碳水吃了、城墙骑了，紧凑但不遗憾。',
   'oneclick-trip-assets/xian-roujiamo-liangpi.png'),

  -- 大理 2 款
  (4, 4, '大理4日环海慢生活', 4, 'MEDIUM', 'RELAXED',
   'Day1 大理古城人民路→复兴路烤乳扇→南门城楼→崇圣寺三塔看倒影→晚上古城民谣酒吧。Day2 海西骑行精华段：才村码头→磻溪S弯→廊桥→喜洲古镇（午餐喜洲粑粑+凉鸡米线）→转角楼和黄墙拍照→下午周城体验白族扎染。'
   'Day3 包车海东线：双廊古镇→玉几岛观景→鹿卧山悬崖拍照→小普陀→文笔村彩虹公路→傍晚理想邦看日落→晚餐野生菌火锅（雨季必吃！）。Day4 苍山感通索道上山→寂照庵满院多肉+素斋→下午大理古城最后逛一圈→买现烤鲜花饼当伴手礼→机场/高铁返程。四天环洱海一圈，不快不慢刚刚好。',
   'oneclick-trip-assets/dali-erhai.png'),

  (9, 4, '大理2日风花雪月速写', 2, 'MEDIUM', 'RELAXED',
   'Day1 龙龛码头看日出→海西骑行到喜洲（S弯、廊桥、稻田拍照）→喜洲粑粑午餐→下午双廊海景咖啡发呆→傍晚理想邦看日落→晚餐古城白族石板烧配酸辣鱼。'
   'Day2 上午崇圣寺三塔→寂照庵素斋→下午古城闲逛买鲜花饼→人民路找家茶馆晒着太阳发呆→烤乳扇配酸奶当下午茶→返程。两天把洱海的日出、喜洲的稻田、双廊的海景、古城的石板路全收进相机，适合周末说走就走。',
   'oneclick-trip-assets/dali-ancient-city.png')
ON DUPLICATE KEY UPDATE
  city_id = VALUES(city_id), title = VALUES(title), days = VALUES(days),
  budget_level = VALUES(budget_level), pace = VALUES(pace),
  summary = VALUES(summary), cover_url = VALUES(cover_url);
