"""种子数据：预设计算机面试题库"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, SessionLocal, Base
from app.models import User, Question

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 创建默认用户
if not db.query(User).filter(User.username == "demo").first():
    db.add(User(username="demo", target_role="后端开发", target_company=""))
    db.commit()

# 面试题库
questions = [
    # 操作系统
    {"category": "操作系统", "difficulty": "medium", "role": "后端开发", "title": "进程和线程的区别",
     "content": "请详细说明进程和线程的区别，包括它们的资源占用、通信方式和切换开销。",
     "answer": "进程是资源分配的基本单位，线程是CPU调度的基本单位。进程拥有独立的地址空间和系统资源，线程共享进程的资源。进程间通信需要IPC（管道、消息队列、共享内存等），线程间可以直接读写共享内存。进程切换开销大（需要切换页表、刷新TLB），线程切换开销小。", "tags": "进程,线程,操作系统基础"},
    {"category": "操作系统", "difficulty": "hard", "role": "后端开发", "title": "死锁的四个必要条件",
     "content": "死锁产生的四个必要条件是什么？如何预防和避免死锁？",
     "answer": "四个必要条件：1.互斥条件 2.持有并等待 3.不可剥夺 4.循环等待。预防：破坏任一条件（如一次性分配资源破坏持有并等待）。避免：银行家算法动态检查资源分配安全性。检测与恢复：定期检测死锁并回滚/终止进程。", "tags": "死锁,并发,操作系统"},
    {"category": "操作系统", "difficulty": "easy", "title": "用户态和内核态",
     "content": "什么是用户态和内核态？为什么要区分？应用程序如何从用户态切换到内核态？",
     "answer": "用户态受限制（不能访问硬件和特权指令），内核态有完整权限。区分为安全和稳定性。切换方式：系统调用、中断、异常。系统调用通过软中断或syscall指令触发。", "tags": "用户态,内核态,系统调用"},
    # 计算机网络
    {"category": "计算机网络", "difficulty": "medium", "role": "后端开发", "title": "TCP三次握手和四次挥手",
     "content": "请详细描述TCP的三次握手和四次挥手过程，为什么握手是三次而挥手是四次？",
     "answer": "三次握手：SYN → SYN-ACK → ACK，确保双方收发能力正常。四次挥手：FIN → ACK → FIN → ACK，因为TCP全双工，关闭需双方各自确认。TIME_WAIT状态持续2MSL确保最后的ACK到达。", "tags": "TCP,握手,挥手,网络"},
    {"category": "计算机网络", "difficulty": "hard", "title": "HTTPS的工作原理",
     "content": "请详细说明HTTPS的工作原理，包括SSL/TLS握手过程和证书验证机制。",
     "answer": "1.客户端发送支持的加密套件和随机数 2.服务端返回证书和随机数 3.客户端验证证书链 4.生成premaster secret用公钥加密发送 5.双方用三个随机数生成对称加密密钥。后续使用对称加密通信。", "tags": "HTTPS,SSL,TLS,网络安全"},
    {"category": "计算机网络", "difficulty": "medium", "title": "HTTP状态码分类",
     "content": "请列出HTTP状态码的分类，并说明常见的状态码含义。",
     "answer": "1xx信息 2xx成功(200/201/204) 3xx重定向(301永久/302临时/304未修改) 4xx客户端错误(400/401/403/404/429) 5xx服务端错误(500/502/503)。RESTful API应正确使用状态码。", "tags": "HTTP,状态码,REST"},
    # 数据库
    {"category": "数据库", "difficulty": "medium", "role": "后端开发", "title": "MySQL索引原理",
     "content": "请说明MySQL InnoDB的索引实现原理，什么是聚集索引和辅助索引？解释最左前缀原则。",
     "answer": "InnoDB使用B+树。聚集索引：叶子节点存完整行数据，按主键排序。辅助索引：叶子节点存主键值，需回表。最左前缀：联合索引(a,b,c)可匹配a, a,b, a,b,c查询，但不能跳过a直接用b。", "tags": "MySQL,索引,B+树,InnoDB"},
    {"category": "数据库", "difficulty": "hard", "title": "事务隔离级别",
     "content": "数据库的四种事务隔离级别分别是什么？各自解决了什么问题？可能出现哪些并发问题？",
     "answer": "读未提交(脏读/不可重复读/幻读)、读已提交(不可重复读/幻读)、可重复读(幻读，MySQL通过间隙锁解决)、串行化(全解决但性能差)。MVCC实现高并发下的隔离。", "tags": "事务,隔离级别,MVCC,并发"},
    {"category": "数据库", "difficulty": "easy", "title": "SQL优化方法",
     "content": "在面试中经常被问到：你做过哪些SQL优化？请分享你的经验。",
     "answer": "1.EXPLAIN分析执行计划 2.合理建索引（避免SELECT *，利用覆盖索引） 3.避免索引失效（函数操作、隐式转换、LIKE前缀通配） 4.大表分页优化(延迟关联) 5.避免大事务 6.读写分离、分库分表", "tags": "SQL优化,索引,性能"},
    # 数据结构
    {"category": "数据结构", "difficulty": "easy", "title": "数组和链表的区别",
     "content": "比较数组和链表的优缺点，分别适用于什么场景？",
     "answer": "数组：连续内存，O(1)随机访问，插入删除O(n)。链表：非连续内存，O(n)随机访问，插入删除O(1)。数组适合读多写少场景；链表适合频繁增删场景。", "tags": "数组,链表,数据结构基础"},
    {"category": "数据结构", "difficulty": "medium", "title": "哈希表的实现原理",
     "content": "哈希表是如何实现的？如何处理哈希冲突？",
     "answer": "哈希函数将key映射到数组索引。冲突解决：链地址法（拉链）、开放寻址法（线性探测、二次探测、双重哈希）。Java HashMap用链地址法+红黑树（链表长度>8时树化）。扩容因子通常0.75。", "tags": "哈希表,HashMap,冲突解决"},
    # 算法
    {"category": "算法", "difficulty": "medium", "title": "快速排序实现",
     "content": "请写出快速排序的实现思路，并分析其时间复杂度和空间复杂度。",
     "answer": "选基准值pivot，分区使左边<右边，递归排序。平均O(nlogn)，最坏O(n²)(已排序数组选首元素)。空间O(logn)(递归栈)。优化：三数取中选pivot、小数组用插入排序、尾递归优化。", "tags": "快排,排序算法,分治"},
    {"category": "算法", "difficulty": "hard", "title": "动态规划解题思路",
     "content": "请说明动态规划的核心思想和解题步骤，并举例说明。",
     "answer": "核心：最优子结构+重叠子问题。步骤：1.定义状态 2.找状态转移方程 3.确定初始条件和边界 4.确定计算顺序。例：背包问题dp[i][w]=max(dp[i-1][w], dp[i-1][w-wi]+vi)。可优化空间到一维。", "tags": "动态规划,DP,算法设计"},
    # Java
    {"category": "Java", "difficulty": "medium", "role": "后端开发", "title": "Java内存模型",
     "content": "请解释Java内存模型(JMM)，包括主内存、工作内存、volatile关键字的作用。",
     "answer": "JMM定义线程和主内存的抽象关系。每个线程有工作内存(缓存)，变量从主内存拷贝。volatile：保证可见性(写立即刷回主内存)、禁止指令重排，但不保证原子性。happens-before原则。", "tags": "Java,JMM,volatile,并发"},
    {"category": "Java", "difficulty": "hard", "title": "垃圾回收机制",
     "content": "请说明JVM的垃圾回收机制，包括常见的GC算法和垃圾收集器。",
     "answer": "判断对象存活：引用计数法、可达性分析(GC Roots)。算法：标记-清除(碎片)、标记-整理、复制(年轻代)。收集器：Serial/ParNew/Parallel Scavenge(年轻代)、CMS/G1(老年代)。G1：Region分区，可预测停顿。", "tags": "JVM,GC,垃圾回收"},
    # 系统设计
    {"category": "系统设计", "difficulty": "hard", "role": "后端开发", "title": "设计一个短链接系统",
     "content": "请设计一个类似短链接服务(TinyURL)的系统，需要考虑高并发和可扩展性。",
     "answer": "1.哈希+Base62编码生成短码 2.发号器(分布式ID:雪花算法) 3.布隆过滤器防重复查询 4.Redis缓存热点链接 5.301重定向 6.分库分表按短码哈希。预估QPS和存储。", "tags": "系统设计,短链接,分布式"},
    {"category": "系统设计", "difficulty": "hard", "title": "设计一个消息队列",
     "content": "从零设计一个消息队列，需要考虑哪些方面？",
     "answer": "核心：生产者→Broker→消费者。考虑：1.存储(顺序写磁盘/分段日志) 2.消费者offset管理 3.消息确认ACK 4.分区与副本 5.顺序消息 6.延迟消息 7.死信队列 8.集群协调(ZK/Raft)。参考Kafka/RocketMQ设计。", "tags": "消息队列,Kafka,系统设计"},
    # Python
    {"category": "Python", "difficulty": "easy", "title": "Python的GIL",
     "content": "什么是Python的GIL（全局解释器锁）？它对多线程编程有什么影响？如何绕过GIL的限制？",
     "answer": "GIL同一时刻只允许一个线程执行Python字节码。影响：CPU密集型多线程反而更慢（切换开销）。绕过：用multiprocessing多进程、用C扩展释放GIL、用asyncio协程处理IO密集型。Python 3.13引入可选无GIL模式。", "tags": "Python,GIL,多线程,多进程"},
    # 并发编程
    {"category": "并发编程", "difficulty": "medium", "role": "后端开发", "title": "乐观锁和悲观锁",
     "content": "请解释乐观锁和悲观锁的概念、实现方式和适用场景。",
     "answer": "悲观锁：认为冲突频繁，先加锁再操作（数据库行锁、synchronized）。乐观锁：假设冲突少，操作后检查版本号/CAS。乐观锁适合读多写少；悲观锁适合写竞争激烈。MySQL中通过version字段或时间戳实现乐观锁。", "tags": "乐观锁,悲观锁,CAS,并发控制"},
    # 分布式
    {"category": "分布式", "difficulty": "hard", "title": "CAP理论和BASE理论",
     "content": "请解释CAP理论和BASE理论，在分布式系统中如何权衡？",
     "answer": "CAP：一致性、可用性、分区容错不可兼得。P必须保证，在C和A间权衡。CP（ZooKeeper）/AP（Eureka）。BASE：基本可用、软状态、最终一致性。实际系统在不同场景选择不同策略。", "tags": "CAP,BASE,分布式理论"},
]

for q in questions:
    existing = db.query(Question).filter(Question.title == q["title"]).first()
    if not existing:
        db.add(Question(
            category=q.get("category", ""),
            difficulty=q.get("difficulty", "medium"),
            role=q.get("role", ""),
            company=q.get("company", ""),
            title=q["title"],
            content=q["content"],
            answer=q.get("answer", ""),
            tags=q.get("tags", ""),
        ))

db.commit()
db.close()
print(f"Seed complete: {len(questions)} questions")
